"""Idempotently deliver automation work to profile-backed conversations."""

import json
import os
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import NAMESPACE_URL, UUID, uuid5

import httpx
from openhands.sdk import RemoteConversation
from openhands.sdk.conversation.request import (
    SendMessageRequest,
    StartConversationRequest,
)
from openhands.sdk.conversation.state import ConversationExecutionStatus
from openhands.sdk.llm.message import TextContent
from openhands.sdk.workspace import LocalWorkspace, RemoteWorkspace

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
# A conditional write that loses a race is retried against a fresh read. The
# store versions the whole state document, not one key, so an unrelated write by
# another automation run can invalidate a conditional write even when the
# registry itself did not change; a handful of retries absorbs that without
# letting a genuinely contended cap be bypassed, because a lost race always
# re-reads before deciding.
_KV_CAS_ATTEMPTS = 8
_KV_CAS_BACKOFF_SECONDS = 0.05


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


class AgentConversationDispatcher:
    """Deliver one revision at a time to a stable conversation for each subject."""

    def __init__(
        self,
        *,
        track_in_flight: bool = False,
        max_in_flight: int | None = None,
    ) -> None:
        self.agent_url = os.environ["AGENT_SERVER_URL"]
        self.api_key = os.environ["SESSION_API_KEY"]
        self.profile_id = UUID(os.environ["AUTOMATION_AGENT_PROFILE_ID"])
        payload = json.loads(os.environ["AUTOMATION_EVENT_PAYLOAD"])
        self.automation_id = str(payload["automation_id"])
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
        # bypass by choosing the other path. None means "no cap": a tracked
        # dispatcher used without one records conversations but never refuses.
        self.max_in_flight = max_in_flight

    def __enter__(self):
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
        assert self._workspace is not None
        return self._workspace.__exit__(*args)

    def deliver(self, subject: str, delivery: str, prompt: str) -> dict[str, str]:
        conversation_id = uuid5(NAMESPACE_URL, f"{self.automation_id}:{subject}")
        state_key = f"{_CONVERSATION_KEY_PREFIX}{conversation_id}"
        record = _kv_value(state_key) or {}
        if self._workspace is None:
            raise RuntimeError("AgentConversationDispatcher must be used as a context")

        same_delivery = record.get("delivery") == delivery

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
                return _deferred(conversation_id)
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
                # The runtime never came up, so the reservation must not hold a
                # slot until it ages out. Releasing must not mask the real error.
                try:
                    self.release(str(conversation_id))
                except Exception:  # noqa: BLE001 - the original error is the news
                    pass
                raise
            disposition = "created"
        try:
            if disposition == "resumed":
                if same_delivery:
                    if (
                        conversation.state.execution_status
                        == ConversationExecutionStatus.RUNNING
                    ):
                        conversation.update_secrets(self._secrets)
                        disposition = "in_progress"
                    elif conversation.state.execution_status in (
                        ConversationExecutionStatus.IDLE,
                        ConversationExecutionStatus.PAUSED,
                    ):
                        # Resuming a stopped conversation starts work, so it
                        # needs a slot too.
                        if not self._admit(str(conversation_id), subject):
                            return _deferred(conversation_id)
                        conversation.update_secrets(self._secrets)
                        conversation.run(blocking=False)
                    else:
                        disposition = "deduplicated"
                else:
                    if not self._admit(str(conversation_id), subject):
                        return _deferred(conversation_id)
                    conversation.update_secrets(self._secrets)
                    conversation.send_message(prompt)
                    conversation.run(blocking=False)
        finally:
            conversation.close()

        if disposition in ("deduplicated", "in_progress"):
            if disposition == "in_progress":
                # A conversation that is still running must be countable even if
                # its creation-time registration did not reach the store.
                self._remember(str(conversation_id), subject)
            return {
                "disposition": disposition,
                "conversation_id": str(conversation_id),
            }

        _kv_put(
            state_key,
            {
                "subject": subject,
                "conversation_id": str(conversation_id),
                "delivery": delivery,
            },
        )
        self._remember(str(conversation_id), subject)
        return {
            "disposition": disposition,
            "conversation_id": str(conversation_id),
        }

    def _prune(self, registry: dict) -> dict:
        """Return only the registry entries that still hold a runtime.

        An entry whose conversation reached a terminal status, or which the
        agent server no longer has, releases its slot. An entry older than the
        abandonment window does too, without a status read, so a scan that died
        before recording a completion does not park a slot forever. An entry
        whose status cannot be read is kept live, so a transient failure never
        lets the deployment overshoot.
        """
        now = time.time()
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
            if status is None or status in _TERMINAL_EXECUTION_STATUSES:
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
        if self._workspace is None:
            raise RuntimeError("AgentConversationDispatcher must be used as a context")
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
        """
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
        if self._workspace is None:
            raise RuntimeError("AgentConversationDispatcher must be used as a context")
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


def _deferred(conversation_id) -> dict[str, str]:
    """The disposition for a delivery refused at the in-flight cap.

    The conversation is not started and its delivery record is not written, so
    the triggering request is not consumed: the next scheduled scan sees the
    same outstanding request and retries it once capacity frees.
    """
    return {"disposition": "deferred", "conversation_id": str(conversation_id)}


def _kv_value(key: str):
    """One key's value, or None when it is absent."""
    body = _kv_request(key, "GET")
    return body.get("value") if body else None


def _kv_put(key: str, value, *, version: int | None = None) -> None:
    """Write one key, optionally only when the document version still matches."""
    query = {"if_version": version} if version is not None else None
    _kv_request(key, "PUT", value, query=query)

