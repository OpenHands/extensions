"""Idempotently deliver automation work to profile-backed conversations."""

import json
import os
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

try:
    import httpx
    from openhands.sdk import RemoteConversation
    from openhands.sdk.conversation.request import (
        SendMessageRequest,
        StartConversationRequest,
    )
    from openhands.sdk.conversation.state import ConversationExecutionStatus
    from openhands.sdk.llm.message import TextContent
    from openhands.sdk.workspace import LocalWorkspace, RemoteWorkspace
except ImportError:
    # A run on OpenHands Cloud or Enterprise has no SDK on its Python path and
    # does not need one: CloudConversations speaks the OpenHands API instead.
    httpx = RemoteConversation = SendMessageRequest = None
    StartConversationRequest = ConversationExecutionStatus = None
    TextContent = LocalWorkspace = RemoteWorkspace = None

_CONVERSATION_KEY_PREFIX = "agent-conversation-"
# Every conversation a dispatcher has started, as `conversation_id: {subject,
# started_at}`. The per-subject records above answer "what delivery did this
# subject last receive"; this index answers "how much work is still live", which
# a scheduled scan needs in order to bound in-flight conversations across runs.
# It is keyed by conversation rather than subject because a worker that reclaims
# capacity has to ask the agent server about a conversation, and the subject is
# the worker's business, not the dispatcher's.
_IN_FLIGHT_KEY = "agent-conversations-in-flight"
# A registry entry older than this is assumed abandoned. The review worker
# abandons a conversation that has not stopped within two hours, and the
# registry has to outlive that so a slot is not recycled while the conversation
# still exists.
_ABANDONED_AFTER_SECONDS = 2 * 60 * 60
_TERMINAL_EXECUTION_STATUSES = frozenset({"finished", "error", "stuck"})
# A slot reserved for a conversation that has not been created yet is held for
# this long before the agent server is believed when it answers 404. The
# reservation is written just before `RemoteConversation.create`, so a
# concurrent admission that reads the registry in that window would otherwise
# prune the reservation as "gone", freeing a slot that is about to be used and
# letting the deployment overshoot its cap. Once the grace has passed, a 404
# really is a conversation that no longer exists and the slot is released. On
# OpenHands Cloud and Enterprise the OpenHands API lists a conversation only once
# its sandbox is up, so a reservation there is held for the longer
# `_CLOUD_START_GRACE_SECONDS` that delivery already allows a start.
_PENDING_GRACE_SECONDS = 3 * 60
# A conditional write that loses a race is retried against a fresh read. The
# store versions the whole state document, not one key, so an unrelated write by
# another automation run can invalidate a conditional write even when the
# registry itself did not change; a handful of retries absorbs that without
# letting a genuinely contended cap be bypassed, because a lost race always
# re-reads before deciding.
_KV_CAS_ATTEMPTS = 8
_KV_CAS_BACKOFF_SECONDS = 0.05

# How long a conversation the OpenHands API was asked to start may take to
# appear before the start is taken to have failed and is made again.
_CLOUD_START_GRACE_SECONDS = 10 * 60
# How long to wait for a paused conversation's sandbox to come back up.
_CLOUD_RESUME_TIMEOUT_SECONDS = 120
_CLOUD_POLL_SECONDS = 3
# A Cloud conversation whose sandbox is paused or gone runs nothing, whatever its
# last execution status said, so it holds no in-flight slot. Waking it again is
# new work, and the delivery that wakes it is admitted again.
_CLOUD_STOPPED_SANDBOX_STATUSES = frozenset({"PAUSED", "ERROR", "MISSING"})
# What `_execution_status` reports for such a conversation.
_SANDBOX_STOPPED = "sandbox_stopped"


class KVConflictError(RuntimeError):
    """A conditional write lost an optimistic-concurrency race."""


def _register_tools() -> None:
    """Register tool models needed to deserialize an attached agent."""
    from openhands.tools import register_default_tools

    register_default_tools()


def _kv_request(
    key: str,
    method: str,
    value: dict | None = None,
    *,
    query: dict | None = None,
) -> dict | None:
    """Call the Automation KV store and return the whole JSON response body.

    `query` carries the store's conditional-write parameters: `meta=true` on a
    read asks for the state version, and `if_version` on a write makes it apply
    only when the document is still at that version. A write that loses that
    check answers 409, which is surfaced as `KVConflictError` so a caller doing
    read-modify-write can re-read and retry rather than clobber a concurrent
    update.
    """
    base_url = os.environ.get("AUTOMATION_API_URL", "").rstrip("/")
    token = os.environ.get("AUTOMATION_KV_TOKEN", "")
    if not base_url or not token:
        raise RuntimeError("Automation KV is required for agent conversation dispatch")
    url = f"{base_url}/v1/kv/{key}"
    if query:
        url = f"{url}?{urlencode(query)}"
    request = Request(
        url,
        data=json.dumps(value).encode() if value is not None else None,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method=method,
    )
    try:
        with urlopen(request, timeout=90) as response:
            body = json.load(response)
    except HTTPError as exc:
        if method == "GET" and exc.code == 404:
            return None
        if method == "PUT" and exc.code == 409:
            raise KVConflictError(f"conditional write to {key} lost a race") from None
        raise
    return body


def _kv_read(key: str) -> tuple:
    """Return `(value, version)` for one key, or `(None, 0)` when absent.

    The version is the Automation KV store's optimistic-concurrency token for
    the whole state document; it is what a conditional write must match for the
    read-modify-write to be atomic across concurrent automation runs.
    """
    body = _kv_request(key, "GET", query={"meta": "true"}) or {}
    return body.get("value"), body.get("version") or 0


class CloudConversations:
    """The conversations of a run on OpenHands Cloud or Enterprise.

    Such a run has no Agent Server to attach to. The OpenHands API starts each
    conversation in a sandbox of its own, which outlives the run's, with the
    agent profile's model, tools and secrets resolved on the server.
    """

    def __init__(self) -> None:
        self.api = os.environ["OPENHANDS_CLOUD_API_URL"].rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {os.environ['OPENHANDS_API_KEY']}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, url: str, body=None, headers=None):
        request = Request(
            url if url.startswith("http") else f"{self.api}{url}",
            data=json.dumps(body).encode() if body is not None else None,
            headers=headers or self.headers,
            method=method,
        )
        with urlopen(request, timeout=90) as response:
            raw = response.read()
        return json.loads(raw) if raw.strip() else {}

    def get(self, conversation_id) -> dict | None:
        """The conversation, or None while the API has no record of it."""
        found = self._request("GET", f"/api/v1/app-conversations?ids={conversation_id}")
        return found[0] if found else None

    def start(self, conversation_id, profile_id, title: str, prompt: str) -> None:
        self._request(
            "POST",
            "/api/v1/app-conversations",
            {
                "conversation_id": str(conversation_id),
                "agent_profile_id": str(profile_id),
                "title": title,
                "initial_message": _user_message(prompt),
            },
        )

    def run(self, conversation: dict) -> None:
        """Start the next turn of an idle conversation on its own Agent Server."""
        try:
            self._request(
                "POST",
                f"{conversation['conversation_url']}/run",
                headers={"X-Session-API-Key": conversation["session_api_key"]},
            )
        except HTTPError as exc:
            if exc.code != 409:  # 409: a turn is already running
                raise

    def send(self, conversation: dict, prompt: str) -> None:
        """Send the next turn, waking the conversation's sandbox if it is paused."""
        conversation_id = conversation["id"]
        if conversation.get("sandbox_status") != "RUNNING":
            self._request(
                "POST", f"/api/v1/sandboxes/{conversation['sandbox_id']}/resume"
            )
            deadline = time.monotonic() + _CLOUD_RESUME_TIMEOUT_SECONDS
            # The execution status is only reported once the sandbox's Agent
            # Server answers, which is when it can take the message.
            while not (self.get(conversation_id) or {}).get("execution_status"):
                if time.monotonic() > deadline:
                    raise RuntimeError(
                        f"Conversation {conversation_id} did not resume in time"
                    )
                time.sleep(_CLOUD_POLL_SECONDS)
        self._request(
            "POST",
            f"/api/v1/app-conversations/{conversation_id}/send-message",
            {**_user_message(prompt), "run": True},
        )


def _user_message(text: str) -> dict:
    return {"role": "user", "content": [{"type": "text", "text": text}]}


class AgentConversationDispatcher:
    """Deliver one revision at a time to a stable conversation for each subject."""

    def __init__(
        self,
        *,
        track_in_flight: bool = False,
        max_in_flight: int | None = None,
    ) -> None:
        # The automation service hands a run the Agent Server URL only on a
        # local Agent Canvas; elsewhere conversations go through the OpenHands API.
        self.agent_url = os.environ.get("AGENT_SERVER_URL")
        self.api_key = os.environ["SESSION_API_KEY"]
        self.profile_id = UUID(os.environ["AUTOMATION_AGENT_PROFILE_ID"])
        payload = json.loads(os.environ["AUTOMATION_EVENT_PAYLOAD"])
        self.automation_id = str(payload["automation_id"])
        self._cloud = None if self.agent_url else CloudConversations()
        self._workspace: RemoteWorkspace | None = None
        self._secrets = {}
        # Only a caller that bounds its work across runs needs the global
        # registry, so it is opt-in and the other automations' dispatchers keep
        # writing exactly one KV record per subject.
        self._track_in_flight = track_in_flight
        # The cap is enforced here, in the dispatcher, because that is where
        # every launch path converges: a scheduled scan's drain and an
        # event-triggered delivery both start conversations through `deliver`,
        # so gating here is what makes admission atomic and impossible to
        # bypass by choosing the other path. It applies on a local Agent Canvas
        # and on OpenHands Cloud and Enterprise alike, because each conversation
        # holds a runtime of its own on either. None means "no cap": a tracked
        # dispatcher used without one records conversations but never refuses.
        self.max_in_flight = max_in_flight

    def __enter__(self):
        if self._cloud:
            return self
        _register_tools()
        self._workspace = RemoteWorkspace(
            host=self.agent_url,
            api_key=self.api_key,
            working_dir=os.environ.get("WORKSPACE_BASE", "/workspace"),
        )
        self._workspace.__enter__()
        self._secrets = self._workspace.get_secrets(
            agent_profile_id=str(self.profile_id)
        )
        return self

    def __exit__(self, *args):
        if self._cloud:
            return None
        assert self._workspace is not None
        return self._workspace.__exit__(*args)

    def deliver(
        self, subject: str, delivery: str, prompt: str, head: str = ""
    ) -> dict[str, str]:
        """Deliver one revision of `subject`, deduping a repeated head.

        `delivery` keys the revision: a second trigger for the same revision
        reuses the conversation without a new turn, and a changed head becomes a
        new delivery. `head` is the revision's commit, and it is the guard that
        matters when two triggers name the same commit - a re-request after the
        bot's own handoff, say - because a delivery key that only counts triggers
        would send a second turn and publish a second review of identical code.
        A conversation already running for this head is reported `in_progress`
        and left alone, whatever the new delivery says. Callers with no revision
        identity leave `head` empty and keep the delivery-key-only behavior.
        """
        conversation_id = uuid5(NAMESPACE_URL, f"{self.automation_id}:{subject}")
        state_key = f"{_CONVERSATION_KEY_PREFIX}{conversation_id}"
        record = _kv_value(state_key) or {}

        same_delivery = record.get("delivery") == delivery
        same_head = bool(head) and record.get("head") == head

        if self._cloud:
            disposition, conversation_id = self._deliver_cloud(
                record, conversation_id, subject, prompt, same_delivery, same_head
            )
        else:
            disposition = self._deliver_local(
                conversation_id, subject, prompt, same_delivery, same_head
            )

        if disposition == "deferred":
            # The deployment is at its in-flight cap: nothing was started and no
            # delivery record is written, so the caller's request is left
            # unconsumed for a later scan to retry.
            return {
                "disposition": disposition,
                "conversation_id": str(conversation_id),
            }
        if disposition in ("deduplicated", "in_progress"):
            if disposition == "in_progress":
                # A conversation that is still running must be countable even if
                # its creation-time registration did not reach the store.
                self._remember(str(conversation_id), subject)
            return {
                "disposition": disposition,
                "conversation_id": str(conversation_id),
            }

        new_record = {
            "subject": subject,
            "conversation_id": str(conversation_id),
            "delivery": delivery,
            "head": head or record.get("head") or "",
        }
        if disposition == "created" and self._cloud:
            new_record["started_at"] = time.time()
        _kv_put(state_key, new_record)
        self._remember(str(conversation_id), subject)
        return {
            "disposition": disposition,
            "conversation_id": str(conversation_id),
        }

    def _deliver_cloud(
        self, record, conversation_id, subject, prompt, same_delivery, same_head
    ):
        """Deliver through the OpenHands API; return the disposition and the id.

        The id is the subject's stable one until its conversation can no longer
        take a turn - its start never completed, or its sandbox is gone - and a
        fresh id from then on, because the API does not start an id twice. The
        KV record carries whichever is current.

        Every branch that starts work - a new conversation, a turn run on an
        idle one, or a revision sent to one whose sandbox may be paused - first
        reserves an in-flight slot, under the id that will actually run. A
        refusal is reported as `deferred` against the subject's current id, and
        nothing is started.
        """
        current_id = record.get("conversation_id") or conversation_id
        conversation = self._cloud.get(current_id)

        if conversation is None:
            started = time.time() - float(record.get("started_at") or 0)
            if started < _CLOUD_START_GRACE_SECONDS:
                # The API is still bringing the subject's conversation up and
                # does not list it yet. Starting another would run two for one
                # subject, so even a new revision waits: the record is left as
                # it is and the next trigger delivers it.
                return "in_progress", current_id
        elif conversation.get("sandbox_status") in ("ERROR", "MISSING"):
            if same_delivery:
                return "deduplicated", current_id
            conversation = None

        if conversation is None:
            new_id = uuid4() if record else conversation_id
            if not self._admit(str(new_id), subject):
                return "deferred", current_id
            try:
                self._cloud.start(new_id, self.profile_id, subject, prompt)
            except Exception:
                self._release_failed_launch(new_id)
                raise
            return "created", new_id

        status = conversation.get("execution_status")
        if status == "running" and (same_delivery or same_head):
            return "in_progress", current_id
        if same_delivery:
            if status in ("idle", "paused"):
                if not self._admit(str(current_id), subject):
                    return "deferred", current_id
                self._cloud.run(conversation)
                return "resumed", current_id
            return "deduplicated", current_id
        if not self._admit(str(current_id), subject):
            return "deferred", current_id
        self._cloud.send(conversation, prompt)
        return "resumed", current_id

    def _deliver_local(
        self, conversation_id, subject, prompt, same_delivery, same_head
    ) -> str:
        if self._workspace is None:
            raise RuntimeError("AgentConversationDispatcher must be used as a context")

        try:
            conversation = RemoteConversation.attach(
                self._workspace, conversation_id, visualizer=None
            )
            disposition = "resumed"
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 404:
                raise
            # Creating launches a runtime, so the slot is reserved first. A
            # deferral here means the deployment is at its cap: no conversation
            # is created and no delivery record is written, so the caller's
            # request is left unconsumed for a later scan to retry.
            if not self._admit(str(conversation_id), subject):
                return "deferred"
            try:
                conversation = RemoteConversation.create(
                    self._workspace,
                    StartConversationRequest(
                        workspace=LocalWorkspace(working_dir="/workspace"),
                        conversation_id=conversation_id,
                        agent_profile_id=self.profile_id,
                        secrets=self._secrets,
                        initial_message=SendMessageRequest(
                            content=[TextContent(text=prompt)], run=True
                        ),
                    ),
                    visualizer=None,
                )
            except Exception:
                self._release_failed_launch(conversation_id)
                raise
            disposition = "created"
        try:
            if disposition == "resumed":
                running = (
                    conversation.state.execution_status
                    == ConversationExecutionStatus.RUNNING
                )
                if running and (same_delivery or same_head):
                    # A turn is already running for this very revision, so a new
                    # trigger is not new work: report the live conversation
                    # rather than starting a second pass beside it.
                    conversation.update_secrets(self._secrets)
                    disposition = "in_progress"
                elif same_delivery:
                    if conversation.state.execution_status in (
                        ConversationExecutionStatus.IDLE,
                        ConversationExecutionStatus.PAUSED,
                    ):
                        # Resuming a stopped conversation starts work, so it
                        # needs a slot too.
                        if not self._admit(str(conversation_id), subject):
                            return "deferred"
                        conversation.update_secrets(self._secrets)
                        conversation.run(blocking=False)
                    else:
                        disposition = "deduplicated"
                else:
                    # A changed head, or a head a human clarified since, is new
                    # work on the same subject: reuse the conversation and send
                    # the revision as its next turn. That starts work, so it
                    # needs a slot too.
                    if not self._admit(str(conversation_id), subject):
                        return "deferred"
                    conversation.update_secrets(self._secrets)
                    conversation.send_message(prompt)
                    conversation.run(blocking=False)
        finally:
            conversation.close()
        return disposition

    def _prune(self, registry: dict) -> dict:
        """Return only the registry entries that still hold a runtime.

        An entry whose conversation reached a terminal status releases its slot,
        and so does a Cloud conversation whose sandbox is paused or gone. An
        entry the server no longer has releases it too, but only once the
        reservation is older than the start grace (`_PENDING_GRACE_SECONDS`, or
        `_CLOUD_START_GRACE_SECONDS` on Cloud): a slot is reserved just before
        its conversation is created, so in that window a 404 means "not created
        yet", not "gone", and freeing it would let a concurrent admission
        overshoot the cap. An entry older than the abandonment window releases
        its slot without a status read, so a scan that died before recording a
        completion does not park a slot forever. An entry whose status cannot be
        read is kept live, so a transient failure never lets the deployment
        overshoot.
        """
        now = time.time()
        grace = _CLOUD_START_GRACE_SECONDS if self._cloud else _PENDING_GRACE_SECONDS
        live = {}
        for conversation_id, entry in registry.items():
            started_at = entry.get("started_at") if isinstance(entry, dict) else None
            try:
                started_at = float(started_at) if started_at else 0.0
            except (TypeError, ValueError):
                started_at = 0.0
            if started_at and now - started_at > _ABANDONED_AFTER_SECONDS:
                continue
            try:
                status = self._execution_status(conversation_id)
            except Exception:
                live[conversation_id] = entry
                continue
            if status is None:
                if started_at and now - started_at <= grace:
                    live[conversation_id] = entry
                continue
            if status in _TERMINAL_EXECUTION_STATUSES or status == _SANDBOX_STOPPED:
                continue
            live[conversation_id] = entry
        return live

    def _write_registry(self, registry: dict, version: int) -> None:
        """Store the registry, applying only if nobody wrote since the read."""
        _kv_put(_IN_FLIGHT_KEY, registry, version=version)

    def _update_registry(self, mutate):
        """Atomically read-modify-write the registry with `mutate`.

        The store versions its whole state document - every key shares one
        `$version` - so a write is applied only if the document is still at the
        version read, and a 409 means another writer got there first and the
        update is retried against fresh state. A registry that does not exist yet
        is created with the store's `nx` operation, which is atomic, so two
        concurrent runs cannot both create it. Returns the resulting registry, or
        None if the write could not be won after the retry budget.
        """
        for attempt in range(_KV_CAS_ATTEMPTS):
            value, version = _kv_read(_IN_FLIGHT_KEY)
            if value is None:
                candidate = mutate({})
                try:
                    _kv_request(
                        _IN_FLIGHT_KEY, "PUT", candidate, query={"nx": "true"}
                    )
                    return candidate
                except KVConflictError:
                    pass
            else:
                registry = value if isinstance(value, dict) else {}
                candidate = mutate(dict(registry))
                if candidate == registry:
                    return registry
                try:
                    self._write_registry(candidate, version)
                    return candidate
                except KVConflictError:
                    pass
            if attempt + 1 < _KV_CAS_ATTEMPTS:
                time.sleep(_KV_CAS_BACKOFF_SECONDS * (attempt + 1))
        return None

    def _admit(self, conversation_id: str, subject: str) -> bool:
        """Atomically reserve a slot for one conversation, or refuse.

        This is the admission gate every launch path passes through. The read,
        the capacity check, and the reservation are one serialized step: the
        registry is written back conditionally on the store's document version,
        so two concurrent automation runs cannot both observe one free slot and
        both start a runtime. A registry that does not exist yet is created with
        the store's atomic `nx` operation, and a write that loses a race is
        retried against a fresh read rather than counted optimistically, so the
        cap holds even under a burst. A conversation already in the registry
        already holds its slot, so re-admitting it (a repeat scan, or an event
        that arrives while a scan runs) costs nothing. When the live count is at
        the cap the caller is refused and should defer, leaving the GitHub
        request unconsumed for a later scan.

        Returns True when the conversation may start or resume, False when the
        deployment is at capacity. A dispatcher that is not tracking, or has no
        configured cap, always admits.
        """
        self._require_context()
        if not self._track_in_flight or self.max_in_flight is None:
            return True
        if self.max_in_flight <= 0:
            return False
        for attempt in range(_KV_CAS_ATTEMPTS):
            value, version = _kv_read(_IN_FLIGHT_KEY)
            registry = value if isinstance(value, dict) else {}
            if value is None:
                # No registry yet: create it with a reservation, atomically.
                candidate = {
                    conversation_id: {
                        "subject": subject,
                        "started_at": time.time(),
                    }
                }
                try:
                    _kv_request(
                        _IN_FLIGHT_KEY, "PUT", candidate, query={"nx": "true"}
                    )
                    return True
                except KVConflictError:
                    pass
            else:
                live = self._prune(registry)
                if conversation_id in live:
                    return True
                if len(live) >= self.max_in_flight:
                    # Persist the pruned view so completed conversations release
                    # their slots even when a scan is refused, then defer.
                    if live != registry:
                        try:
                            self._write_registry(live, version)
                        except KVConflictError:
                            pass
                    return False
                candidate = dict(live)
                candidate[conversation_id] = {
                    "subject": subject,
                    "started_at": time.time(),
                }
                try:
                    self._write_registry(candidate, version)
                    return True
                except KVConflictError:
                    pass
            if attempt + 1 < _KV_CAS_ATTEMPTS:
                time.sleep(_KV_CAS_BACKOFF_SECONDS * (attempt + 1))
        # Could not win a slot against concurrent writers. Refuse rather than
        # launch ungated: the caller defers and a later scan retries.
        return False

    def _remember(self, conversation_id: str, subject: str) -> None:
        """Record a conversation so a later scan can count it as live.

        This corrects the ledger for a conversation that is already running
        (for example one whose creation-time registration did not reach the
        store); it does not enforce the cap, because the runtime already
        exists by the time it is called.
        """
        if not self._track_in_flight:
            return

        def add(registry):
            if conversation_id in registry:
                return registry
            registry[conversation_id] = {
                "subject": subject,
                "started_at": time.time(),
            }
            return registry

        self._update_registry(add)

    def _execution_status(self, conversation_id: str) -> str | None:
        """One conversation's status, or None when the server no longer has it.

        A WebSocket subscription is not needed to ask, so this reads the REST
        endpoint directly rather than attaching, which keeps the count cheap
        even when several conversations are live.

        On OpenHands Cloud and Enterprise the OpenHands API is asked instead. A
        conversation whose sandbox is paused or gone reports `_SANDBOX_STOPPED`,
        and one whose sandbox is still starting has no execution status yet but
        already holds a runtime, so it reports `starting`.
        """
        if self._cloud:
            conversation = self._cloud.get(conversation_id)
            if conversation is None:
                return None
            if conversation.get("sandbox_status") in _CLOUD_STOPPED_SANDBOX_STATUSES:
                return _SANDBOX_STOPPED
            return conversation.get("execution_status") or "starting"
        assert self._workspace is not None
        response = self._workspace.client.get(
            f"/api/conversations/{conversation_id}"
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json().get("execution_status")

    def in_flight(self) -> int | None:
        """Count this dispatcher's nonterminal conversations, pruning the rest.

        A scheduled scan starts more reviews only when the count is below its
        configured maximum, so this is the capacity signal that bounds how many
        runtimes exist at once. Completed and errored conversations release their
        slot, a conversation the server no longer has releases it, and an entry
        left behind by a scan that died before recording a completion goes stale
        after `_ABANDONED_AFTER_SECONDS` and releases it too. Unknown statuses
        count as live, so a transient read failure never lets the scan overshoot.

        This is a snapshot for planning; the authoritative bound is `_admit`,
        which reserves a slot atomically at launch time. None means this
        dispatcher was not asked to track its work, and the caller should fall
        back to its own per-run bound rather than read the empty registry as
        "nothing is running".
        """
        self._require_context()
        if not self._track_in_flight:
            return None
        value, version = _kv_read(_IN_FLIGHT_KEY)
        if value is None:
            return 0
        registry = value if isinstance(value, dict) else {}
        live = self._prune(registry)
        if live != registry:
            try:
                self._write_registry(live, version)
            except KVConflictError:
                pass
        return len(live)

    def release(self, conversation_id: str) -> None:
        """Drop one conversation from the registry, freeing its slot."""
        if not self._track_in_flight:
            return

        def drop(registry):
            registry.pop(str(conversation_id), None)
            return registry

        self._update_registry(drop)

    def _release_failed_launch(self, conversation_id) -> None:
        """Free the slot reserved for a launch that raised.

        The runtime never came up, so the reservation must not hold a slot until
        it ages out. Releasing must not mask the launch's own error.
        """
        try:
            self.release(str(conversation_id))
        except Exception:  # noqa: BLE001 - the original error is the news
            pass

    def _require_context(self) -> None:
        """Refuse use outside `with`, where a local run has no Agent Server yet.

        A Cloud run speaks the OpenHands API and needs no workspace to be open.
        """
        if not self._cloud and self._workspace is None:
            raise RuntimeError("AgentConversationDispatcher must be used as a context")


def _kv_value(key: str):
    """One key's value, or None when it is absent."""
    body = _kv_request(key, "GET")
    return body.get("value") if body else None


def _kv_put(key: str, value, *, version: int | None = None) -> None:
    """Write one key, optionally only when the document version still matches."""
    query = {"if_version": version} if version is not None else None
    _kv_request(key, "PUT", value, query=query)
