"""OpenHands API (legacy V0) client.

This file is intentionally:
- small (easy to copy into other repos)
- dependency-light (only `requests`)
- opinionated in a helpful way (defaults to OpenHands Cloud)

Audience: AI agents.

If you are an AI agent reading this, here is the recommended workflow:
1) Start a conversation: POST /api/conversations
2) (Optional) monitor progress via GET /api/conversations/{id}
3) (Optional) read event stream via GET /api/conversations/{id}/events
4) (Optional) fetch full event history via GET /api/conversations/{id}/trajectory

Source of truth for endpoint shapes:
https://github.com/OpenHands/OpenHands/tree/main/openhands/server/routes

Docs:
https://docs.openhands.dev/api-reference/new-conversation
"""

from __future__ import annotations

import argparse
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import requests


DEFAULT_BASE_URL = 'https://app.all-hands.dev'


TerminalConversationStatus = Literal[
    # Most common terminal states observed in the API/docs
    'STOPPED',
    'ERROR',
    'FAILED',
    'CANCELLED',
]


@dataclass(frozen=True)
class OpenHandsAPIConfig:
    api_key: str
    base_url: str = DEFAULT_BASE_URL


class OpenHandsAPI:
    """A minimal OpenHands REST API client (legacy V0 routes).

    Notes:
    - Auth: `Authorization: Bearer <OPENHANDS_API_KEY>`
    - base_url defaults to the hosted OpenHands Cloud.

    Design choice: keep responses as raw dicts.
    This makes it easy for AI agents to explore fields returned by the server
    without maintaining a strict schema here.
    """

    def __init__(self, api_key: str | None = None, base_url: str = DEFAULT_BASE_URL):
        resolved_key = api_key or os.getenv('OPENHANDS_API_KEY')
        if not resolved_key:
            raise ValueError(
                'Missing API key. Set OPENHANDS_API_KEY or pass api_key=...'
            )

        self._cfg = OpenHandsAPIConfig(api_key=resolved_key, base_url=base_url.rstrip('/'))
        self._session = requests.Session()
        self._session.headers.update(
            {
                'Authorization': f'Bearer {self._cfg.api_key}',
                'Content-Type': 'application/json',
            }
        )

    @property
    def base_url(self) -> str:
        return self._cfg.base_url

    # -----------------------------
    # Core REST endpoints
    # -----------------------------

    def create_conversation(
        self,
        initial_user_msg: str,
        repository: str | None = None,
        selected_branch: str | None = None,
        git_provider: str | None = None,
        conversation_instructions: str | None = None,
    ) -> dict[str, Any]:
        """POST /api/conversations

        This is the entry point for most automations.

        Args:
            initial_user_msg: The first user message.
            repository: Optional "owner/repo" to attach.
            selected_branch: Optional git branch.
            git_provider: Optional provider hint ("github", "gitlab", ...).
            conversation_instructions: Optional extra instructions.

        Returns:
            Dict with at least: conversation_id, status (and often url).
        """

        payload: dict[str, Any] = {'initial_user_msg': initial_user_msg}
        if repository:
            payload['repository'] = repository
        if selected_branch:
            payload['selected_branch'] = selected_branch
        if git_provider:
            payload['git_provider'] = git_provider
        if conversation_instructions:
            payload['conversation_instructions'] = conversation_instructions

        r = self._session.post(f'{self.base_url}/api/conversations', json=payload)
        r.raise_for_status()
        return r.json()

    def get_conversation(self, conversation_id: str) -> dict[str, Any]:
        """GET /api/conversations/{conversation_id}"""
        r = self._session.get(f'{self.base_url}/api/conversations/{conversation_id}')
        r.raise_for_status()
        return r.json()

    def get_events(
        self,
        conversation_id: str,
        *,
        start_id: int = 0,
        end_id: int | None = None,
        reverse: bool = False,
        limit: int = 20,
    ) -> dict[str, Any]:
        """GET /api/conversations/{conversation_id}/events

        This is the most useful endpoint for incremental monitoring.

        The server enforces limit <= 100.
        """
        limit = max(1, min(100, int(limit)))
        params: dict[str, Any] = {
            'start_id': start_id,
            'reverse': str(bool(reverse)).lower(),
            'limit': limit,
        }
        if end_id is not None:
            params['end_id'] = end_id

        r = self._session.get(
            f'{self.base_url}/api/conversations/{conversation_id}/events', params=params
        )
        r.raise_for_status()
        return r.json()

    def get_trajectory(self, conversation_id: str) -> dict[str, Any]:
        """GET /api/conversations/{conversation_id}/trajectory

        This usually returns the entire trajectory/event history (heavier than /events).
        """
        r = self._session.get(
            f'{self.base_url}/api/conversations/{conversation_id}/trajectory'
        )
        r.raise_for_status()
        return r.json()

    def list_conversations(
        self,
        *,
        limit: int = 20,
        page_id: str | None = None,
        selected_repository: str | None = None,
        include_sub_conversations: bool | None = None,
    ) -> dict[str, Any]:
        """GET /api/conversations

        Returns a paginated result set: { results: [...], next_page_id: ... }.
        """
        params: dict[str, Any] = {'limit': max(1, int(limit))}
        if page_id:
            params['page_id'] = page_id
        if selected_repository:
            params['selected_repository'] = selected_repository
        if include_sub_conversations is not None:
            params['include_sub_conversations'] = str(bool(include_sub_conversations)).lower()

        r = self._session.get(f'{self.base_url}/api/conversations', params=params)
        r.raise_for_status()
        return r.json()

    def update_conversation_title(self, conversation_id: str, title: str) -> dict[str, Any]:
        """PATCH /api/conversations/{conversation_id}

        Useful to set a deterministic title for automation-created conversations.
        """
        r = self._session.patch(
            f'{self.base_url}/api/conversations/{conversation_id}', json={'title': title}
        )
        r.raise_for_status()
        return r.json()

    def delete_conversation(self, conversation_id: str) -> dict[str, Any]:
        """DELETE /api/conversations/{conversation_id}"""
        r = self._session.delete(f'{self.base_url}/api/conversations/{conversation_id}')
        r.raise_for_status()
        return r.json()

    def add_message(self, conversation_id: str, message: str) -> dict[str, Any]:
        """POST /api/conversations/{conversation_id}/message

        Sends a user message into an existing conversation.
        """
        r = self._session.post(
            f'{self.base_url}/api/conversations/{conversation_id}/message',
            json={'message': message},
        )
        r.raise_for_status()
        return r.json()

    def list_workspace_files(
        self, conversation_id: str, path: str | None = None
    ) -> list[str] | dict[str, Any]:
        """GET /api/conversations/{conversation_id}/list-files

        Returns a list of files in the sandbox workspace.
        """
        params: dict[str, Any] = {}
        if path is not None:
            params['path'] = path
        r = self._session.get(
            f'{self.base_url}/api/conversations/{conversation_id}/list-files', params=params
        )
        r.raise_for_status()
        return r.json()

    def get_file_content(self, conversation_id: str, file_path: str) -> dict[str, Any]:
        """GET /api/conversations/{conversation_id}/select-file?file=...

        Returns { code: "..." } for text files.
        """
        r = self._session.get(
            f'{self.base_url}/api/conversations/{conversation_id}/select-file',
            params={'file': file_path},
        )
        r.raise_for_status()
        return r.json()

    # -----------------------------
    # Convenience helpers
    # -----------------------------

    def create_conversation_from_prompt_files(
        self,
        prompt_file: str | Path,
        *,
        repository: str | None = None,
        selected_branch: str | None = None,
        append_file: str | Path | None = None,
    ) -> dict[str, Any]:
        """Create a conversation from a prompt file (optionally append another file).

        This mirrors the pattern used in automation workflows:
        - keep a main prompt template
        - keep a small shared "tail" with conventions

        Note: we do not implement jinja rendering here on purpose.
        (Agents can add it if they need templates.)
        """

        main_text = Path(prompt_file).read_text(encoding='utf-8')
        if append_file and Path(append_file).exists():
            tail = Path(append_file).read_text(encoding='utf-8')
            initial = f'{main_text}\n\n{tail}'
        else:
            initial = main_text

        return self.create_conversation(
            initial_user_msg=initial,
            repository=repository,
            selected_branch=selected_branch,
        )

    def poll_until_terminal(
        self,
        conversation_id: str,
        *,
        timeout_s: int = 20 * 60,
        poll_interval_s: int = 30,
    ) -> dict[str, Any]:
        """Poll GET /api/conversations/{id} until terminal.

        Terminal states are not strictly standardized; we handle a safe set.
        If you observe a new terminal status in practice, add it here.
        """
        start = time.time()
        while time.time() - start < timeout_s:
            convo = self.get_conversation(conversation_id)
            status = str(convo.get('status') or '').upper()
            if status in ('STOPPED', 'ERROR', 'FAILED', 'CANCELLED'):
                return convo
            time.sleep(poll_interval_s)

        raise TimeoutError(
            f'Conversation {conversation_id} did not reach a terminal state within {timeout_s}s'
        )


# -----------------------------
# Small CLI
# -----------------------------

def _cmd_new_conversation(args: argparse.Namespace) -> int:
    api = OpenHandsAPI(api_key=args.api_key, base_url=args.base_url)

    common_append = args.append_file
    resp = api.create_conversation_from_prompt_files(
        args.prompt_file,
        repository=args.repo,
        selected_branch=args.branch,
        append_file=common_append,
    )

    conversation_id = resp.get('conversation_id', '')
    url = resp.get('url') or (f'{api.base_url}/conversations/{conversation_id}' if conversation_id else None)

    # Print a human-useful URL first (fits GH actions logs, etc.)
    if url:
        print(url)
    else:
        print(resp)

    if args.poll and conversation_id:
        final = api.poll_until_terminal(
            conversation_id,
            timeout_s=args.timeout_s,
            poll_interval_s=args.poll_interval_s,
        )
        print(final)

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='openhands_api.py')
    sub = parser.add_subparsers(dest='cmd', required=True)

    p_new = sub.add_parser('new-conversation', help='Create a new conversation from a prompt file')
    p_new.add_argument('--api-key', default=None, help='Defaults to OPENHANDS_API_KEY env var')
    p_new.add_argument('--base-url', default=DEFAULT_BASE_URL, help=f'Default: {DEFAULT_BASE_URL}')
    p_new.add_argument('--prompt-file', required=True, help='Path to a markdown/text prompt file')
    p_new.add_argument('--append-file', default=None, help='Optional second file to append (e.g., a common tail)')
    p_new.add_argument('--repo', default=None, help='Optional owner/repo')
    p_new.add_argument('--branch', default=None, help='Optional git branch')
    p_new.add_argument('--poll', action='store_true', help='Poll until terminal and print final state')
    p_new.add_argument('--timeout-s', type=int, default=20 * 60)
    p_new.add_argument('--poll-interval-s', type=int, default=30)
    p_new.set_defaults(func=_cmd_new_conversation)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == '__main__':
    raise SystemExit(main())
