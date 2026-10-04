"""Idempotently deliver automation work to profile-backed conversations."""

import json
import os
import time
from urllib.error import HTTPError
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

# How long a conversation the OpenHands API was asked to start may take to
# appear before the start is taken to have failed and is made again.
_CLOUD_START_GRACE_SECONDS = 10 * 60
# How long to wait for a paused conversation's sandbox to come back up.
_CLOUD_RESUME_TIMEOUT_SECONDS = 120
_CLOUD_POLL_SECONDS = 3
# How many times a matched delivery whose conversation ended in ERROR is sent
# again. The delivery key never changes for a stable subject, so without a
# retry its work is stranded; without a bound, a conversation that fails the
# same way every time would be re-run on every scan.
_MAX_ERROR_RETRIES = 2


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

    def __init__(self) -> None:
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
        record = _kv_request(state_key, "GET") or {}

        same_delivery = record.get("delivery") == delivery
        same_head = bool(head) and record.get("head") == head
        # Error retries count against one delivery; a new delivery starts over.
        error_retries = int(record.get("error_retries") or 0) if same_delivery else 0
        can_retry = error_retries < _MAX_ERROR_RETRIES

        if self._cloud:
            disposition, conversation_id = self._deliver_cloud(
                record,
                conversation_id,
                subject,
                prompt,
                same_delivery,
                same_head,
                can_retry,
            )
        else:
            disposition = self._deliver_local(
                conversation_id, prompt, same_delivery, same_head, can_retry
            )

        if disposition in ("deduplicated", "in_progress"):
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
        if disposition == "retried":
            error_retries += 1
        if error_retries:
            new_record["error_retries"] = error_retries
        _kv_request(state_key, "PUT", new_record)
        return {
            "disposition": disposition,
            "conversation_id": str(conversation_id),
        }

    def _deliver_cloud(
        self,
        record,
        conversation_id,
        subject,
        prompt,
        same_delivery,
        same_head,
        can_retry,
    ):
        """Deliver through the OpenHands API; return the disposition and the id.

        The id is the subject's stable one until its conversation can no longer
        take a turn - its start never completed, or its sandbox is gone - and a
        fresh id from then on, because the API does not start an id twice. The
        KV record carries whichever is current.
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
            self._cloud.start(new_id, self.profile_id, subject, prompt)
            return "created", new_id

        status = conversation.get("execution_status")
        if status == "running" and (same_delivery or same_head):
            return "in_progress", current_id
        if same_delivery:
            if status in ("idle", "paused"):
                self._cloud.run(conversation)
                return "resumed", current_id
            if status == "error" and can_retry:
                # The delivery matched but its conversation died before the work
                # finished, so send the revision again rather than strand it.
                # The API reports an execution status only while the sandbox
                # runs, so an errored conversation whose sandbox was already
                # paused is not seen here and keeps reporting deduplicated.
                self._cloud.send(conversation, prompt)
                return "retried", current_id
            return "deduplicated", current_id
        self._cloud.send(conversation, prompt)
        return "resumed", current_id

    def _deliver_local(
        self, conversation_id, prompt, same_delivery, same_head, can_retry
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
                    elif (
                        conversation.state.execution_status
                        == ConversationExecutionStatus.ERROR
                        and can_retry
                    ):
                        # The delivery matched but its conversation died before
                        # the work finished, so send the revision again rather
                        # than strand it.
                        conversation.update_secrets(self._secrets)
                        conversation.send_message(prompt)
                        conversation.run(blocking=False)
                        disposition = "retried"
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
        return disposition
