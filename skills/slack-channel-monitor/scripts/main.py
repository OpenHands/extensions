"""
Slack Channel Monitor  -  OpenHands Automation Script

Polls monitored Slack channels every minute, including messages inside threads
(not just top-level posts). When a message containing the trigger phrase is
detected it:
  1. Adds a 👀 reaction to acknowledge the message.
  2. Creates an OpenHands conversation pre-loaded with the message and recent
     context (thread context if the trigger lives inside a thread, otherwise
     recent channel history).
  3. Posts a reply in the Slack thread with a link to the conversation.

If the trigger arrives in a thread that already has an open OpenHands
conversation, that conversation is reused instead of starting a new one.

On subsequent runs:
  - New replies in a tracked thread are forwarded to the running conversation.
  - When the conversation reaches a terminal/idle state the agent's final
    response (or an error notice) is posted back to the Slack thread.

Configuration constants are embedded at automation-creation time by the skill.
See SKILL.md for the full setup workflow.

Required secrets (set in OpenHands Settings → Secrets):
  SLACK_BOT_TOKEN    -  bot token (xoxb-…)   with scopes:
                        channels:history, channels:read,
                        reactions:write, chat:write
  OR
  SLACK_USER_TOKEN   -  user token (xoxp-…)  with scopes:
                        channels:history, search:read (for multi-channel),
                        reactions:write, chat:write

Optional secret:
  OPENHANDS_URL      -  base URL of your OpenHands instance for conversation
                      links (default: http://localhost:8000)
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from urllib.parse import urlencode

# ── Embedded configuration (filled in by the skill at creation time) ──────────
TRIGGER_PHRASE = "@openhands"
CHANNEL_IDS: list[str] = []          # e.g. ["C0123456789", "C9876543210"]
DEFAULT_OPENHANDS_URL = "http://localhost:8000"

# Lookback slightly over 60s to avoid missing messages at cron boundaries
# when poll interval jitter causes slight delays.
INITIAL_LOOKBACK = 70

# Prevent posting summaries in the same run that created the conversation,
# avoiding race conditions with conversation startup.
DONE_DEBOUNCE = 15

# Rolling window size for bot message deduplication - sized to handle
# ~1 week of continuous operation at high message rates.
MAX_BOT_TS = 2000

# Limit context to avoid overwhelming the agent with too much history.
CONTEXT_MESSAGE_LIMIT = 15

# How far back (seconds) to look for context when creating a new conversation.
CONTEXT_LOOKBACK_SECONDS = 3600  # 1 hour of recent messages for context

# Cap on persisted thread parents per channel. Threads remain pollable across
# runs even after their parent message ages out of the channel history window;
# this bound keeps the state file small and the per-run `conversations.replies`
# call count well under Slack's Tier 3 limit (~50 req/min) for typical setups.
MAX_KNOWN_THREADS_PER_CHANNEL = 50


# ── Stdlib helpers ─────────────────────────────────────────────────────────────

def _get_env_key() -> str:
    return (
        os.environ.get("SESSION_API_KEY")
        or os.environ.get("OH_SESSION_API_KEYS_0")
        or ""
    )


def get_secret(name: str) -> str:
    """Fetch a named secret from the agent server."""
    url = os.environ.get("AGENT_SERVER_URL", "").rstrip("/")
    key = _get_env_key()
    req = urllib.request.Request(
        f"{url}/api/settings/secrets/{name}",
        headers={"X-Session-API-Key": key},
    )
    with urllib.request.urlopen(req) as r:
        return r.read().decode().strip()


def fire_callback(
    status: str = "COMPLETED",
    error: str | None = None,
    conversation_id: str | None = None,
) -> None:
    """Signal run completion to the automation service."""
    url = os.environ.get("AUTOMATION_CALLBACK_URL", "")
    if not url:
        return
    body: dict = {"status": status, "run_id": os.environ.get("AUTOMATION_RUN_ID", "")}
    if error:
        body["error"] = error
    if conversation_id:
        body["conversation_id"] = conversation_id
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('AUTOMATION_CALLBACK_API_KEY', '')}",
        },
    )
    try:
        urllib.request.urlopen(req)
    except Exception as exc:
        print(f"Callback error (non-fatal): {exc}")


# ── State management ───────────────────────────────────────────────────────────

def _state_file_path() -> str:
    """Derive a persistent storage path from WORKSPACE_BASE.

    WORKSPACE_BASE = {root}/automation-runs/{run_id}
    State lives two levels up at {root}/automation-state/.
    """
    workspace_base = os.environ.get("WORKSPACE_BASE", "")
    event_payload = json.loads(os.environ.get("AUTOMATION_EVENT_PAYLOAD", "{}"))
    automation_id = event_payload.get("automation_id", "default")

    if workspace_base:
        root = os.path.dirname(os.path.dirname(os.path.abspath(workspace_base)))
    else:
        root = os.path.expanduser("~/.openhands/workspaces")

    state_dir = os.path.join(root, "automation-state")
    os.makedirs(state_dir, exist_ok=True)
    return os.path.join(state_dir, f"slack_poller_{automation_id}.json")


def load_state(path: str) -> dict:
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {
        "version": 1,
        "bot_user_id": None,
        "last_poll": {},           # channel_id → float timestamp string
        "conversations": {},       # conv_key → ConversationRecord (see schema docs)
        "bot_message_ts": [],      # ts strings of messages posted by this bot
        "known_threads": {},       # channel_id → {thread_ts: latest_reply_ts}
    }


def save_state(path: str, state: dict) -> None:
    with open(path, "w") as f:
        json.dump(state, f, indent=2)


# ── Slack API helpers ──────────────────────────────────────────────────────────

def _slack_call(
    token: str,
    method: str,
    endpoint: str,
    params: dict | None = None,
    body: dict | None = None,
) -> dict:
    """Low-level Slack API call. Raises RuntimeError on API errors."""
    url = f"https://slack.com/api/{endpoint}"
    if params:
        url = f"{url}?{urlencode(params)}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req) as r:
        result = json.loads(r.read())
    if not result.get("ok"):
        raise RuntimeError(f"Slack {endpoint}: {result.get('error', 'unknown_error')}")
    return result


def slack_get(token: str, endpoint: str, params: dict | None = None) -> dict:
    return _slack_call(token, "GET", endpoint, params=params)


def slack_post(token: str, endpoint: str, body: dict) -> dict:
    return _slack_call(token, "POST", endpoint, body=body)


def _slack_auth_test(token: str) -> tuple[str, set[str]]:
    """Call auth.test, verify the token, and return (user_id, scopes).

    Reads the X-OAuth-Scopes response header so callers can gate behaviour on
    individual scopes without making extra API calls.  Raises RuntimeError if
    the token is rejected by Slack.
    """
    req = urllib.request.Request(
        "https://slack.com/api/auth.test",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req) as r:
        scopes_header: str = r.headers.get("X-OAuth-Scopes", "")
        result = json.loads(r.read())
    if not result.get("ok"):
        raise RuntimeError(f"Slack token rejected: {result.get('error')}")
    scopes = (
        {s.strip() for s in scopes_header.split(",") if s.strip()}
        if scopes_header else set()
    )
    return result.get("user_id", ""), scopes


def add_reaction(token: str, channel: str, ts: str, emoji: str = "eyes") -> None:
    try:
        slack_post(token, "reactions.add", {"channel": channel, "name": emoji, "timestamp": ts})
    except RuntimeError as exc:
        if "already_reacted" not in str(exc):
            print(f"  Warning: reactions.add failed: {exc}")


def post_message(token: str, channel: str, text: str, thread_ts: str | None = None) -> str:
    """Post a Slack message and return its timestamp."""
    body: dict = {"channel": channel, "text": text}
    if thread_ts:
        body["thread_ts"] = thread_ts
    return slack_post(token, "chat.postMessage", body).get("ts", "")


def channel_history(token: str, channel: str, oldest: str, limit: int = 100) -> list[dict]:
    result = slack_get(token, "conversations.history", {
        "channel": channel,
        "oldest": oldest,
        "limit": limit,
        "inclusive": "false",
    })
    return result.get("messages", [])


def thread_replies(token: str, channel: str, thread_ts: str, oldest: str) -> list[dict]:
    """Fetch replies in a thread newer than oldest."""
    result = slack_get(token, "conversations.replies", {
        "channel": channel,
        "ts": thread_ts,
        "oldest": oldest,
        "limit": 100,
        "inclusive": "false",
    })
    messages = result.get("messages", [])
    # conversations.replies includes the parent; drop it
    return [m for m in messages if m.get("ts") != thread_ts]


def search_trigger_messages(
    token: str, channel_ids: list[str], trigger: str, oldest_ts: str
) -> list[dict]:
    """Search for trigger messages across channels (user token with search:read).

    Uses the search query approach which avoids N per-channel history calls.
    Results are post-filtered by timestamp since search only supports date-level
    precision in the 'after:' modifier.
    """
    channel_filter = " ".join(f"in:<#{cid}>" for cid in channel_ids)
    oldest_dt = datetime.fromtimestamp(float(oldest_ts), tz=timezone.utc)
    # Use yesterday's date to ensure we catch all messages since our timestamp
    date_str = oldest_dt.strftime("%Y-%m-%d")
    query = f'"{trigger}" {channel_filter} after:{date_str}'
    result = slack_get(token, "search.messages", {
        "query": query,
        "count": 100,
        "sort": "timestamp",
        "sort_dir": "asc",
    })
    matches = result.get("messages", {}).get("matches", [])
    # Post-filter to our precise oldest timestamp
    return [m for m in matches if float(m.get("ts", "0")) > float(oldest_ts)]


def has_search_permission(scopes: set[str]) -> bool:
    return "search:read" in scopes


# ── OpenHands Agent Server helpers ────────────────────────────────────────────

def _oh_request(
    agent_url: str, api_key: str, method: str, path: str, body: dict | None = None
) -> dict:
    url = f"{agent_url}{path}"
    headers = {"X-Session-API-Key": api_key, "Content-Type": "application/json"}
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read()
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode()
        raise RuntimeError(f"Agent API {method} {path} → {exc.code}: {body_text}") from exc


def _get_agent_dict(agent_url: str, api_key: str) -> dict:
    """Fetch configured agent settings and return a serialised Agent dict.

    Uses X-Expose-Secrets: plaintext so the LLM api_key is a real string
    rather than a masked placeholder.  The result is passed as the 'agent'
    field (not 'agent_settings') to avoid a double-registration bug: the
    agent_settings code path calls create_agent() during request validation
    AND again during StoredConversation construction, both of which try to
    register the same usage_id in the LLM registry.
    """
    url = f"{agent_url}/api/settings"
    headers = {"X-Session-API-Key": api_key, "X-Expose-Secrets": "plaintext"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"GET /api/settings failed: {exc.code}") from exc
    agent_settings = data.get("agent_settings", {})
    llm = agent_settings.get("llm", {})
    # settings["agent_settings"]["agent"] reflects the full-app agent registry
    # (e.g. "CodeActAgent", "BrowsingAgent").  The automation SDK is a separate
    # runtime whose only valid kind is "Agent" — never forward that value.
    return {
        "kind": "Agent",
        "llm": llm,
        # "terminal" and "file_editor" are the runtime-registered tool names.
        # Without an explicit tools list the SDK Agent defaults to think+finish only.
        "tools": [{"name": "terminal"}, {"name": "file_editor"}],
    }


def create_conversation(agent_url: str, api_key: str, initial_message: str) -> str:
    """Create a conversation and return its ID.

    The server auto-starts the agent when initial_message is provided
    (conversation_service calls send_message(..., run=True)), so no
    separate POST to /run is needed or wanted — it would 409.
    """
    workspace_dir = os.environ.get("WORKSPACE_BASE", "/workspace")
    agent = _get_agent_dict(agent_url, api_key)
    result = _oh_request(agent_url, api_key, "POST", "/api/conversations", {
        "workspace": {"working_dir": workspace_dir},
        "agent": agent,
        "initial_message": {"content": [{"text": initial_message}]},
    })
    return result["id"]


def send_to_conversation(agent_url: str, api_key: str, conv_id: str, text: str) -> None:
    """Send a user message to an existing conversation and resume the agent."""
    _oh_request(agent_url, api_key, "POST", f"/api/conversations/{conv_id}/events", {
        "role": "user",
        "content": [{"text": text}],
        "run": True,
    })


def conversation_status(agent_url: str, api_key: str, conv_id: str) -> str:
    result = _oh_request(agent_url, api_key, "GET", f"/api/conversations/{conv_id}")
    return result.get("execution_status", "unknown")


def conversation_final_response(agent_url: str, api_key: str, conv_id: str) -> str:
    result = _oh_request(
        agent_url, api_key, "GET", f"/api/conversations/{conv_id}/agent_final_response"
    )
    return result.get("response", "")


# ── Message filtering ──────────────────────────────────────────────────────────

def _is_human_message(msg: dict, bot_user_id: str, bot_message_ts: list[str]) -> bool:
    """Return True if the message was posted by a human and not by this bot."""
    if msg.get("bot_id"):
        return False
    if msg.get("subtype"):
        return False
    if msg.get("user") == bot_user_id:
        return False
    if msg.get("ts") in bot_message_ts:
        return False
    return True


# ── Polling helpers ────────────────────────────────────────────────────────────

def _resolve_slack_token() -> tuple[str, bool]:
    """Try SLACK_USER_TOKEN then SLACK_BOT_TOKEN; return (token, is_user).
    Raises RuntimeError if neither is set.
    """
    for secret_name, is_user in [("SLACK_USER_TOKEN", True), ("SLACK_BOT_TOKEN", False)]:
        try:
            val = get_secret(secret_name)
            if val:
                print(f"Using {secret_name}")
                return val, is_user
        except Exception:
            pass
    raise RuntimeError(
        "No Slack token found. Set SLACK_BOT_TOKEN or SLACK_USER_TOKEN in "
        "OpenHands Settings → Secrets."
    )


def _verify_token_scopes(scopes: set[str]) -> bool:
    """Validate required scopes; return can_react.
    Raises RuntimeError if a mandatory scope is absent.
    If scopes header was absent, allows the API to fail at point of use.
    """
    if not scopes:
        # X-OAuth-Scopes header absent (unusual); proceed and let the API
        # return errors at the point of use rather than blocking everything.
        return True
    read_scopes = {"channels:history", "groups:history", "im:history", "mpim:history"}
    if not (scopes & read_scopes):
        raise RuntimeError(
            "Slack token is missing a read scope. "
            f"Required: one of {sorted(read_scopes)}. "
            f"Token has: {sorted(scopes)}"
        )
    if "chat:write" not in scopes:
        raise RuntimeError(
            "Slack token is missing the chat:write scope. "
            f"Token has: {sorted(scopes)}"
        )
    can_react: bool = "reactions:write" in scopes
    if not can_react:
        print("Note: reactions:write scope absent - 👀 reactions will be skipped")
    return can_react


def _gather_channel_context(
    slack_token: str,
    channel_id: str,
    before_ts: str,
    bot_user_id: str,
    bot_message_ts: list[str],
    limit: int = CONTEXT_MESSAGE_LIMIT,
) -> list[str]:
    """Gather recent human messages from a channel for context."""
    context_lines: list[str] = []
    try:
        cutoff = str(float(before_ts) - CONTEXT_LOOKBACK_SECONDS)
        msgs = channel_history(slack_token, channel_id, cutoff, limit)
        for msg in reversed(msgs):
            if _is_human_message(msg, bot_user_id, bot_message_ts):
                context_lines.append(f"[{msg.get('user','?')}]: {msg.get('text','')}")
    except Exception:
        pass  # context is best-effort
    return context_lines


def _gather_thread_context(
    slack_token: str,
    channel_id: str,
    thread_ts: str,
    before_ts: str,
    bot_user_id: str,
    bot_message_ts: list[str],
    limit: int = CONTEXT_MESSAGE_LIMIT,
) -> list[str]:
    """Gather messages from a Slack thread (parent + earlier replies).

    Used when the trigger phrase arrives inside an existing thread - the
    thread's own messages are usually more relevant context than channel-wide
    history.  Stops collecting once `before_ts` is reached so the trigger
    message itself (and anything posted after it) is not duplicated.
    """
    context_lines: list[str] = []
    try:
        result = slack_get(slack_token, "conversations.replies", {
            "channel": channel_id,
            "ts": thread_ts,
            "limit": limit + 1,
            "inclusive": "true",
        })
        before_f = float(before_ts)
        for msg in result.get("messages", []):
            if float(msg.get("ts", "0")) >= before_f:
                break
            if _is_human_message(msg, bot_user_id, bot_message_ts):
                context_lines.append(f"[{msg.get('user','?')}]: {msg.get('text','')}")
    except Exception:
        pass  # context is best-effort
    return context_lines


def _poll_new_messages(
    slack_token: str,
    use_search: bool,
    oldest_by_channel: dict[str, str],
    global_oldest: str,
    active_convs: dict[str, dict],
    known_threads: dict[str, dict[str, str]],
) -> list[tuple[str, dict]]:
    """Collect and sort new top-level messages and thread replies from Slack.

    Thread discovery sources combined here:
      - Brand-new thread parents observed in this poll's channel history.
      - Threads with active OpenHands conversations (so user replies are
        forwarded even when no new history is returned).
      - Previously-seen threads persisted in `known_threads`. This keeps
        threads pollable across runs even after the parent ages out of the
        history window, so a trigger phrase posted as a reply still gets
        picked up.

    `known_threads` is mutated in place with the latest reply timestamp seen
    for each thread.
    """
    new_messages: list[tuple[str, dict]] = []
    threads_to_poll: dict[str, set[str]] = {cid: set() for cid in CHANNEL_IDS}

    # Seed thread discovery with tracked conversations and persisted threads.
    for rec in active_convs.values():
        if rec.get("status") == "closed":
            continue
        cid = rec["channel_id"]
        if cid in threads_to_poll:
            threads_to_poll[cid].add(rec["thread_ts"])
    for cid, threads in known_threads.items():
        if cid in threads_to_poll:
            threads_to_poll[cid].update(threads.keys())

    if use_search:
        try:
            matches = search_trigger_messages(slack_token, CHANNEL_IDS, TRIGGER_PHRASE, global_oldest)
            for m in matches:
                cid = m.get("channel", {}).get("id", "")
                if cid in CHANNEL_IDS:
                    ch_oldest = oldest_by_channel.get(cid, global_oldest)
                    if float(m.get("ts", "0")) > float(ch_oldest):
                        new_messages.append((cid, m))
            print(f"search.messages returned {len(new_messages)} trigger candidate(s)")
        except Exception as exc:
            print(f"search.messages failed ({exc}), falling back to conversations.history")
            use_search = False

    if not use_search:
        for cid in CHANNEL_IDS:
            oldest = oldest_by_channel[cid]
            try:
                msgs = channel_history(slack_token, cid, oldest)
                for m in msgs:
                    new_messages.append((cid, m))
                    # Any top-level message that's the parent of a thread - even
                    # one whose latest reply predates this poll - needs to be
                    # registered so future runs can fetch later replies.
                    if m.get("reply_count", 0) > 0:
                        threads_to_poll[cid].add(m.get("ts", ""))
                print(f"  {cid}: {len(msgs)} new message(s) since {oldest}")
            except Exception as exc:
                print(f"  Warning: could not fetch history for {cid}: {exc}")

    reply_messages: list[tuple[str, dict]] = []
    for cid, thread_set in threads_to_poll.items():
        oldest = oldest_by_channel.get(cid, global_oldest)
        for thread_ts in thread_set:
            try:
                replies = thread_replies(slack_token, cid, thread_ts, oldest)
            except Exception as exc:
                print(f"  Warning: could not fetch replies for thread {thread_ts} in {cid}: {exc}")
                continue
            for r in replies:
                reply_messages.append((cid, r))
            latest_ts = thread_ts
            if replies:
                latest_ts = max(
                    (r.get("ts", thread_ts) for r in replies),
                    key=lambda t: float(t or "0"),
                    default=thread_ts,
                )
            known_threads.setdefault(cid, {})[thread_ts] = latest_ts

    # Dedupe by (channel, ts): conversations.history can return a brand-new
    # thread parent that we also schedule for reply polling. `thread_replies`
    # already drops the parent, but guarding here keeps the code robust if
    # that behaviour ever changes.
    seen: set[tuple[str, str]] = set()
    deduped: list[tuple[str, dict]] = []
    for cid, m in new_messages + reply_messages:
        key = (cid, m.get("ts", ""))
        if key in seen:
            continue
        seen.add(key)
        deduped.append((cid, m))

    return sorted(deduped, key=lambda x: float(x[1].get("ts", "0")))


def _prune_known_threads(known_threads: dict[str, dict[str, str]]) -> None:
    """Keep at most MAX_KNOWN_THREADS_PER_CHANNEL most recent threads per channel."""
    for cid, threads in list(known_threads.items()):
        if cid not in CHANNEL_IDS:
            # Channel no longer monitored - drop entirely.
            del known_threads[cid]
            continue
        if len(threads) <= MAX_KNOWN_THREADS_PER_CHANNEL:
            continue
        kept = sorted(
            threads.items(), key=lambda kv: float(kv[1] or "0"), reverse=True
        )[:MAX_KNOWN_THREADS_PER_CHANNEL]
        known_threads[cid] = dict(kept)


def _process_trigger_message(
    slack_token: str,
    agent_url: str,
    api_key: str,
    openhands_url: str,
    channel_id: str,
    msg_ts: str,
    text: str,
    thread_root: str,
    conv_key: str,
    active_convs: dict[str, dict],
    bot_message_ts: list[str],
    bot_user_id: str,
    can_react: bool,
) -> str | None:
    """React to a trigger message, create an OpenHands conversation, and post a link.

    Returns the new conversation ID on success, or None on error.
    """
    print(f"  Trigger detected in {channel_id} at {msg_ts}: {text[:80]}")
    if can_react:
        add_reaction(slack_token, channel_id, msg_ts)

    # When the trigger arrived inside an existing thread (thread_root != msg_ts),
    # the thread's own history is more relevant than channel-wide chatter.
    if thread_root != msg_ts:
        context_lines = _gather_thread_context(
            slack_token, channel_id, thread_root, msg_ts, bot_user_id, bot_message_ts
        )
        context_label = "Recent thread context (oldest → newest):"
    else:
        context_lines = _gather_channel_context(
            slack_token, channel_id, msg_ts, bot_user_id, bot_message_ts
        )
        context_label = "Recent channel context (oldest → newest):"
    context_block = "\n".join(context_lines) if context_lines else "(no recent context)"

    # Wrap the context in a 4-backtick fenced code block so:
    #   * `---` separators don't get interpreted as setext H2 headings
    #     (which made the context label render as a giant heading), and
    #   * any markdown-looking characters in user-supplied Slack text
    #     (`# foo`, `* bar`, `_baz_`, etc.) render verbatim.
    # 4 backticks tolerate up to 3 consecutive backticks inside Slack text;
    # users posting `````` ` ``````` would still break out, but it's vanishingly rare.
    initial_prompt = (
        f"You are an AI assistant responding to a message in a Slack channel.\n\n"
        f"Channel ID : {channel_id}\n"
        f"Thread root: {thread_root}\n"
        f"Trigger msg: {text}\n\n"
        f"{context_label}\n\n"
        f"````\n{context_block}\n````\n\n"
        f"Please analyse the request and take the appropriate action. "
        f"When you are finished, summarise what you did clearly  -  that "
        f"summary will be posted back to the Slack thread."
    )

    try:
        conv_id = create_conversation(agent_url, api_key, initial_prompt)
        conv_url = f"{openhands_url}/conversations/{conv_id}"

        active_convs[conv_key] = {
            "conversation_id": conv_id,
            "channel_id": channel_id,
            "thread_ts": thread_root,
            "status": "active",
            "last_activity": time.time(),
        }

        link_text = f"🤖 On it! View progress here: {conv_url}"
        ts_back = post_message(slack_token, channel_id, link_text, thread_ts=thread_root)
        if ts_back:
            bot_message_ts.append(ts_back)

        print(f"  Created conversation {conv_id} ({conv_url})")
        return conv_id
    except Exception as exc:
        print(f"  Error creating conversation for {conv_key}: {exc}")
        return None


def _check_conversation_completion(
    conv_key: str,
    rec: dict,
    agent_url: str,
    api_key: str,
    slack_token: str,
    bot_message_ts: list[str],
) -> None:
    """Post the agent's final response to the Slack thread when the conversation finishes."""
    last_activity: float = rec.get("last_activity", 0.0)
    if (time.time() - last_activity) < DONE_DEBOUNCE:
        return

    conv_id = rec["conversation_id"]
    channel_id = rec["channel_id"]
    thread_ts = rec["thread_ts"]

    try:
        status = conversation_status(agent_url, api_key, conv_id)
    except Exception as exc:
        print(f"  Warning: could not get status for {conv_id}: {exc}")
        return

    print(f"  {conv_key} → status={status}")

    if status in ("idle", "finished", "error", "stuck"):
        try:
            final = conversation_final_response(agent_url, api_key, conv_id)
        except Exception:
            final = ""

        if status in ("error", "stuck"):
            summary = (
                f"⚠️ The agent encountered a problem (status: *{status}*)."
                + (f"\n\n{final}" if final else "")
            )
        else:
            summary = f"✅ Done!\n\n{final}" if final else "✅ Task complete (no summary available)."

        ts_back = post_message(slack_token, channel_id, summary, thread_ts=thread_ts)
        if ts_back:
            bot_message_ts.append(ts_back)

        rec["status"] = "closed"
        print(f"  Posted summary for {conv_key}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> str | None:
    """Run one polling cycle. Returns the last conversation ID created, if any."""
    state_path = _state_file_path()
    state = load_state(state_path)

    agent_url = os.environ.get("AGENT_SERVER_URL", "").rstrip("/")
    api_key = _get_env_key()

    slack_token, token_is_user = _resolve_slack_token()

    try:
        openhands_url = get_secret("OPENHANDS_URL").rstrip("/") or DEFAULT_OPENHANDS_URL
    except Exception:
        openhands_url = DEFAULT_OPENHANDS_URL

    # Raises RuntimeError immediately if the token is invalid - no point polling.
    bot_user_id_new, scopes = _slack_auth_test(slack_token)
    state["bot_user_id"] = bot_user_id_new
    print(f"Bot user ID: {bot_user_id_new}")

    can_react = _verify_token_scopes(scopes)

    bot_user_id: str = state.get("bot_user_id") or ""
    bot_message_ts: list[str] = state.get("bot_message_ts", [])
    now_ts = str(time.time())

    use_search = (
        token_is_user
        and len(CHANNEL_IDS) > 1
        and has_search_permission(scopes)
    )
    print(f"Polling strategy: {'search.messages' if use_search else 'conversations.history'}")

    oldest_by_channel: dict[str, str] = {
        cid: state["last_poll"].get(cid, str(time.time() - INITIAL_LOOKBACK))
        for cid in CHANNEL_IDS
    }
    global_oldest = min(oldest_by_channel.values())

    active_convs: dict[str, dict] = state.get("conversations", {})
    known_threads: dict[str, dict[str, str]] = state.get("known_threads", {})

    all_incoming = _poll_new_messages(
        slack_token, use_search, oldest_by_channel, global_oldest,
        active_convs, known_threads,
    )

    for cid in CHANNEL_IDS:
        state["last_poll"][cid] = now_ts

    last_conversation_id: str | None = None
    for channel_id, msg in all_incoming:
        if not _is_human_message(msg, bot_user_id, bot_message_ts):
            continue

        msg_ts: str = msg.get("ts", "")
        text: str = msg.get("text", "") or ""
        thread_ts: str | None = msg.get("thread_ts")

        # thread_root is the TS we use as the conversation key.
        # For top-level messages it's the message itself; for replies it's the parent.
        thread_root: str = thread_ts if thread_ts and thread_ts != msg_ts else msg_ts
        conv_key = f"{channel_id}:{thread_root}"

        has_trigger = TRIGGER_PHRASE.lower() in text.lower()
        existing = active_convs.get(conv_key)
        is_open_existing = existing is not None and existing.get("status") != "closed"

        # ── Case A: this thread already has an open conversation - reuse it.
        # Applies to plain replies AND to in-thread trigger phrases: the user
        # asked for thread-scoped conversation reuse, so we never create a
        # second conversation for the same thread.
        if is_open_existing:
            assert existing is not None  # narrow for type checkers
            print(f"  Forwarding {msg_ts} → conversation {existing['conversation_id']}")
            try:
                send_to_conversation(
                    agent_url, api_key, existing["conversation_id"],
                    f"User said in Slack thread: {text}",
                )
                existing["status"] = "active"
                existing["last_activity"] = time.time()
            except Exception as exc:
                print(f"  Warning: failed to forward message: {exc}")
            if has_trigger and can_react:
                add_reaction(slack_token, channel_id, msg_ts)
            continue

        # ── Case B: trigger phrase in a thread/message with no open conversation
        # (either brand-new or one that's already been closed) - create one.
        if has_trigger:
            conv_id = _process_trigger_message(
                slack_token, agent_url, api_key, openhands_url,
                channel_id, msg_ts, text, thread_root, conv_key,
                active_convs, bot_message_ts, bot_user_id, can_react,
            )
            if conv_id:
                last_conversation_id = conv_id

    for conv_key, rec in list(active_convs.items()):
        if rec.get("status") != "closed":
            _check_conversation_completion(
                conv_key, rec, agent_url, api_key, slack_token, bot_message_ts,
            )

    if len(bot_message_ts) > MAX_BOT_TS:
        state["bot_message_ts"] = bot_message_ts[-MAX_BOT_TS:]
    else:
        state["bot_message_ts"] = bot_message_ts

    _prune_known_threads(known_threads)

    state["conversations"] = active_convs
    state["known_threads"] = known_threads
    save_state(state_path, state)
    print(f"State saved to {state_path}")
    return last_conversation_id


try:
    conversation_id = main()
    fire_callback("COMPLETED", conversation_id=conversation_id)
except Exception as exc:
    import traceback
    traceback.print_exc()
    fire_callback("FAILED", str(exc))
    sys.exit(1)
