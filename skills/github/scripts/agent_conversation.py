"""Idempotently deliver automation work to profile-backed conversations."""

import json
import os
import time
from urllib.error import HTTPError
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


def _register_tools() -> None:
    """Register tool models needed to deserialize an attached agent."""
    from openhands.tools import register_default_tools

    register_default_tools()


def _kv_request(key: str, method: str, value: dict | None = None) -> dict | None:
    base_url = os.environ.get("AUTOMATION_API_URL", "").rstrip("/")
    token = os.environ.get("AUTOMATION_KV_TOKEN", "")
    if not base_url or not token:
        raise RuntimeError("Automation KV is required for agent conversation dispatch")
    request = Request(
        f"{base_url}/v1/kv/{key}",
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
        raise
    return body.get("value") if method == "GET" else body


class AgentConversationDispatcher:
    """Deliver one revision at a time to a stable conversation for each subject."""

    def __init__(self, *, track_in_flight: bool = False) -> None:
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
        record = _kv_request(state_key, "GET") or {}
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
                        conversation.update_secrets(self._secrets)
                        conversation.run(blocking=False)
                    else:
                        disposition = "deduplicated"
                else:
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

        _kv_request(
            state_key,
            "PUT",
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

    def _registry(self) -> dict:
        """Every conversation this dispatcher has started, or {}."""
        value = _kv_request(_IN_FLIGHT_KEY, "GET")
        return value if isinstance(value, dict) else {}

    def _remember(self, conversation_id: str, subject: str) -> None:
        """Record a conversation so a later scan can count it as live."""
        if not self._track_in_flight:
            return
        registry = self._registry()
        if conversation_id in registry:
            return
        registry[conversation_id] = {"subject": subject, "started_at": time.time()}
        _kv_request(_IN_FLIGHT_KEY, "PUT", registry)

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

        None means this dispatcher was not asked to track its work, and the
        caller should fall back to its own per-run bound rather than read the
        empty registry as "nothing is running".
        """
        if self._workspace is None:
            raise RuntimeError("AgentConversationDispatcher must be used as a context")
        if not self._track_in_flight:
            return None
        registry = self._registry()
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
        if live != registry:
            _kv_request(_IN_FLIGHT_KEY, "PUT", live)
        return len(live)

    def release(self, conversation_id: str) -> None:
        """Drop one conversation from the registry, freeing its slot."""
        if not self._track_in_flight:
            return
        registry = self._registry()
        if registry.pop(str(conversation_id), None) is not None:
            _kv_request(_IN_FLIGHT_KEY, "PUT", registry)
