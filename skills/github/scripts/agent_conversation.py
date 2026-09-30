"""Idempotently deliver automation work to profile-backed conversations."""

import json
import os
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

    def __init__(self) -> None:
        self.agent_url = os.environ["AGENT_SERVER_URL"]
        self.api_key = os.environ["SESSION_API_KEY"]
        self.profile_id = UUID(os.environ["AUTOMATION_AGENT_PROFILE_ID"])
        payload = json.loads(os.environ["AUTOMATION_EVENT_PAYLOAD"])
        self.automation_id = str(payload["automation_id"])
        self._workspace: RemoteWorkspace | None = None
        self._secrets = {}

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
        record = _kv_request(state_key, "GET") or {}
        if self._workspace is None:
            raise RuntimeError("AgentConversationDispatcher must be used as a context")

        same_delivery = record.get("delivery") == delivery
        same_head = bool(head) and record.get("head") == head

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
                        conversation.update_secrets(self._secrets)
                        conversation.run(blocking=False)
                    else:
                        disposition = "deduplicated"
                else:
                    # A changed head, or a head a human clarified since, is new
                    # work on the same subject: reuse the conversation and send
                    # the revision as its next turn.
                    conversation.update_secrets(self._secrets)
                    conversation.send_message(prompt)
                    conversation.run(blocking=False)
        finally:
            conversation.close()

        if disposition in ("deduplicated", "in_progress"):
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
                "head": head or record.get("head") or "",
            },
        )
        return {
            "disposition": disposition,
            "conversation_id": str(conversation_id),
        }
