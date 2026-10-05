"""Idempotently deliver automation work to profile-backed conversations."""

import json
import os
import time
from collections.abc import Callable
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

    def agent_profiles(self) -> list[dict]:
        listing = self._request("GET", "/api/agent-profiles")
        return (listing or {}).get("profiles") or []

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


def _render(prompt, conversation_id) -> str:
    """The text of `prompt` for the conversation it is delivered to.

    A caller that must name the receiving conversation in its own prompt (a
    marker the deterministic side later looks for, say) passes a function of
    the conversation id, because only delivery decides which conversation that
    is.
    """
    return prompt(str(conversation_id)) if callable(prompt) else prompt


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
        self,
        subject: str,
        delivery: str,
        prompt: str | Callable[[str], str],
        head: str = "",
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
        `prompt` may be a function of the receiving conversation's id.
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

    def subject_conversation(self, subject: str) -> str | None:
        """The conversation this automation currently delivers `subject` to."""
        conversation_id = uuid5(NAMESPACE_URL, f"{self.automation_id}:{subject}")
        record = _kv_request(f"{_CONVERSATION_KEY_PREFIX}{conversation_id}", "GET")
        return (record or {}).get("conversation_id") or None

    def llm_provenance(self, conversation_id: str) -> tuple[str, str] | None:
        """The LLM profile name and model a conversation runs, or None if it is gone.

        Both are read back from the conversation, never from the automation's
        current settings: the server resolves the agent profile when it starts
        the conversation, and a reused conversation keeps that LLM after the
        profile is edited. The model is the conversation's own. The LLM profile
        name comes from the launching agent profile only while that profile is
        still at its launch revision, and is `unknown` otherwise.
        """
        if self._cloud:
            conversation = self._cloud.get(conversation_id)
            if conversation is None:
                return None
            model = conversation.get("llm_model")
        else:
            try:
                conversation = self._agent_server_get(
                    f"/api/conversations/{conversation_id}"
                )
            except HTTPError as exc:
                if exc.code == 404:
                    return None
                raise
            model = ((conversation.get("agent") or {}).get("llm") or {}).get("model")
        launched = conversation.get("launched_agent_profile") or {}
        profile = "unknown"
        if launched.get("agent_profile_id"):
            try:
                if self._cloud:
                    profiles = self._cloud.agent_profiles()
                else:
                    listing = self._agent_server_get("/api/agent-profiles")
                    profiles = (listing or {}).get("profiles") or []
            except Exception as exc:  # noqa: BLE001 - the model is still known
                print(f"Could not read agent profiles: {type(exc).__name__}: {exc}")
                profiles = []
            for item in profiles:
                if str(item.get("id")) == str(launched["agent_profile_id"]):
                    if item.get("revision") == launched.get("revision"):
                        profile = item.get("llm_profile_ref") or "unknown"
                    break
        return profile, model or "unknown"

    def _agent_server_get(self, path: str) -> dict:
        request = Request(
            f"{self.agent_url.rstrip('/')}{path}",
            headers={"X-Session-API-Key": self.api_key},
        )
        with urlopen(request, timeout=90) as response:
            return json.load(response)

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
            self._cloud.start(
                new_id, self.profile_id, subject, _render(prompt, new_id)
            )
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
                self._cloud.send(conversation, _render(prompt, current_id))
                return "retried", current_id
            return "deduplicated", current_id
        self._cloud.send(conversation, _render(prompt, current_id))
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
                        content=[TextContent(text=_render(prompt, conversation_id))],
                        run=True,
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
                        conversation.send_message(_render(prompt, conversation_id))
                        conversation.run(blocking=False)
                        disposition = "retried"
                    else:
                        disposition = "deduplicated"
                else:
                    # A changed head, or a head a human clarified since, is new
                    # work on the same subject: reuse the conversation and send
                    # the revision as its next turn.
                    conversation.update_secrets(self._secrets)
                    conversation.send_message(_render(prompt, conversation_id))
                    conversation.run(blocking=False)
        finally:
            conversation.close()
        return disposition

    def review_snapshot(self, conversation_id):
        if self._cloud:
            conversation = self._cloud.get(conversation_id)
            if conversation is None:
                return "missing", ""
            status = conversation.get("execution_status", "unknown")
            if status != "finished":
                return status, ""
            result = self._cloud._request(
                "GET",
                f"{conversation['conversation_url']}/agent_final_response",
                headers={"X-Session-API-Key": conversation["session_api_key"]},
            )
            return status, result.get("response", "")
        headers = {"X-Session-API-Key": self.api_key}
        base = f"{self.agent_url.rstrip('/')}/api/conversations/{conversation_id}"
        try:
            with urlopen(Request(base, headers=headers), timeout=90) as response:
                status = json.load(response).get("execution_status", "unknown")
        except HTTPError as exc:
            if exc.code == 404:
                return "missing", ""
            raise
        if status != "finished":
            return status, ""
        with urlopen(
            Request(base + "/agent_final_response", headers=headers), timeout=90
        ) as response:
            return status, json.load(response).get("response", "")

    def start_review_work(self, conversation_id, subject, prompt):
        if self._cloud:
            self._cloud.start(UUID(conversation_id), self.profile_id, subject, prompt)
            return
        if self._workspace is None:
            raise RuntimeError("Dispatcher must be used as a context")
        conversation = RemoteConversation.create(
            self._workspace,
            StartConversationRequest(
                workspace=LocalWorkspace(working_dir="/workspace"),
                conversation_id=UUID(conversation_id),
                agent_profile_id=self.profile_id,
                secrets=self._secrets,
                initial_message=SendMessageRequest(
                    content=[TextContent(text=prompt)], run=True
                ),
            ),
            visualizer=None,
        )
        conversation.close()


class ReviewCoordination:
    """CAS against the automation service's shared, user-authorized KV namespace."""

    def __init__(self):
        namespace = os.environ.get("REVIEW_COORDINATION_AUTOMATION_ID")
        key = os.environ.get("REVIEW_COORDINATION_API_KEY")
        if not namespace or not key:
            raise RuntimeError(
                "Structured reviews require shared coordination namespace and API key"
            )
        self.query = urlencode({"automation_id": str(UUID(namespace))})
        self.base = os.environ["AUTOMATION_API_URL"].rstrip("/")
        self.headers = {"X-Session-API-Key": key, "Content-Type": "application/json"}

    def request(self, key, method="GET", value=None, condition=""):
        request = Request(
            f"{self.base}/v1/kv/{key}?{self.query}&{condition}",
            data=None if value is None else json.dumps(value).encode(),
            headers=self.headers,
            method=method,
        )
        try:
            with urlopen(request, timeout=90) as response:
                return json.load(response)
        except HTTPError as exc:
            if method == "GET" and exc.code == 404:
                return None
            raise

    def claim(self, subject, *, existing_only=False):
        key = "review-work-" + str(uuid5(NAMESPACE_URL, subject))
        for _ in range(5):
            current = self.request(key, condition="meta=true")
            if current is None and existing_only:
                return None
            value = (current or {}).get("value") or {}
            if value.get("lease_until", 0) > time.time():
                return None
            value = {**value, "owner": str(uuid4()), "lease_until": time.time() + 180}
            condition = f"if_version={current['version']}" if current else "nx=true"
            try:
                self.request(key, "PUT", value, condition)
                return ReviewLease(self, key, value)
            except HTTPError as exc:
                if exc.code != 409:
                    raise
        return None


class ReviewLease:
    def __init__(self, store, key, value):
        self.store, self.key, self.value = store, key, value
        self.owner = value["owner"]

    def save(self, **changes):
        for _ in range(5):
            current = self.store.request(self.key, condition="meta=true")
            value = current["value"]
            if (
                value.get("owner") != self.owner
                or value.get("lease_until", 0) <= time.time()
            ):
                raise RuntimeError("Review lease lost; refusing side effects")
            updated = {**self.value, **changes}
            try:
                self.store.request(
                    self.key, "PUT", updated, f"if_version={current['version']}"
                )
                self.value = updated
                return
            except HTTPError as exc:
                if exc.code != 409:
                    raise
        raise RuntimeError("Review coordination contention; retry next scan")

    def release(self):
        self.save(lease_until=0)
