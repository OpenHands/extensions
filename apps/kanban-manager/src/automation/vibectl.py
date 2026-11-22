#!/usr/bin/env python3
"""Command-line board control for the Vibe Manager agent.

Replaces the curl calls the manager used to make against the vibe-manager
service. The manager runs in a terminal, so a CLI is a more direct interface
than an HTTP API that existed only to be curled from the same machine.

Every command prints JSON on stdout. Errors print a JSON object with an
"error" key and exit non-zero, so the agent can tell failure from success
without parsing prose.

    vibectl.py snapshot
    vibectl.py patch <ticket_id> --status in_progress --title "🐛 Fix login"
    vibectl.py dispatch --ticket <ticket_id> --prompt-file task.md --title "🎫 Fix login"
    vibectl.py followup <conversation_id> --prompt-file msg.md
    vibectl.py profiles
    vibectl.py conversation <conversation_id>
"""

from __future__ import annotations

import argparse
import json
import os
import sys


def _defaults() -> dict:
    """Workspace defaults written next to the CLI when it was installed.

    The manager agent runs in its own shell and does not inherit the
    automation run's environment, so the workspace it manages — and the store
    it lives in — are recorded on disk rather than passed through env vars.
    """
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}


DEFAULTS = _defaults()
# Must be set before vibestore is imported: it resolves the store root lazily,
# but every command below depends on pointing at the right store.
if DEFAULTS.get("store_dir"):
    os.environ.setdefault("VIBE_STORE_DIR", DEFAULTS["store_dir"])

import vibestore  # noqa: E402 - VIBE_STORE_DIR must be set first


def _out(payload) -> int:
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _read_prompt(args) -> str:
    if args.prompt_file:
        with open(args.prompt_file, encoding="utf-8") as fh:
            return fh.read()
    if args.prompt:
        return args.prompt
    raise ValueError("provide --prompt or --prompt-file")


def cmd_snapshot(args) -> int:
    return _out(vibestore.snapshot(args.workspace_id))


def cmd_patch(args) -> int:
    fields = {
        k: v for k, v in {
            "status": args.status,
            "title": args.title,
            "conversation_id": args.conversation_id,
            "pr_url": args.pr_url,
            "manager_note": args.manager_note,
            "dispatched_entry_count": args.dispatched_entry_count,
            "append_entry": args.append_entry,
        }.items() if v is not None
    }
    if not fields:
        raise ValueError("no fields to patch")
    return _out(vibestore.patch_ticket(args.workspace_id, args.ticket_id, **fields))


def cmd_dispatch(args) -> int:
    return _out(vibestore.start_conversation(
        args.working_dir,
        _read_prompt(args),
        title=args.title,
        llm_profile=args.profile,
        role=args.role,
        worktree=not args.no_worktree,
        ws_id=args.workspace_id,
        ticket_id=args.ticket,
    ))


def cmd_followup(args) -> int:
    return _out(vibestore.start_conversation(
        args.working_dir,
        _read_prompt(args),
        llm_profile=args.profile,
        conversation_id=args.conversation_id,
        ws_id=args.workspace_id,
        ticket_id=args.ticket,
    ))


def cmd_profiles(args) -> int:
    return _out(vibestore.llm_profiles())


def cmd_conversation(args) -> int:
    conv = vibestore.agent_request(
        f"/api/conversations/{args.conversation_id}?include_skills=false", timeout=30
    )
    out = {
        "id": conv.get("id"),
        "execution_status": conv.get("execution_status"),
        "title": conv.get("title"),
        "model": ((conv.get("agent") or {}).get("llm") or {}).get("model"),
    }
    if args.final_response:
        try:
            out["final_response"] = vibestore.agent_request(
                f"/api/conversations/{args.conversation_id}/agent_final_response",
                timeout=30,
            )
        except Exception as exc:
            out["final_response_error"] = str(exc)
    return _out(out)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="vibectl.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--workspace-id", default=None,
                   help="defaults to VIBE_WORKSPACE_ID")
    p.add_argument("--working-dir", default=None,
                   help="project path; defaults to VIBE_WORKSPACE_PATH")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("snapshot", help="print the board").set_defaults(func=cmd_snapshot)

    patch = sub.add_parser("patch", help="update a ticket")
    patch.add_argument("ticket_id")
    patch.add_argument("--status", choices=list(vibestore.STATUSES))
    patch.add_argument("--title")
    patch.add_argument("--conversation-id")
    patch.add_argument("--pr-url")
    patch.add_argument("--manager-note")
    patch.add_argument("--dispatched-entry-count", type=int)
    patch.add_argument("--append-entry")
    patch.set_defaults(func=cmd_patch)

    dispatch = sub.add_parser("dispatch", help="start a worker conversation")
    dispatch.add_argument("--prompt")
    dispatch.add_argument("--prompt-file")
    dispatch.add_argument("--title")
    dispatch.add_argument("--profile", help="LLM profile name")
    dispatch.add_argument("--ticket", help="ticket this worker is for; the model "
                                           "requested on it overrides --profile")
    dispatch.add_argument("--role", default="worker", choices=["worker", "manager"])
    dispatch.add_argument("--no-worktree", action="store_true",
                          help="run in the checkout instead of an isolation worktree")
    dispatch.set_defaults(func=cmd_dispatch)

    followup = sub.add_parser("followup", help="message an existing conversation")
    followup.add_argument("conversation_id")
    followup.add_argument("--prompt")
    followup.add_argument("--prompt-file")
    followup.add_argument("--profile", help="switch the conversation to this profile")
    followup.add_argument("--ticket", help="ticket this conversation is for; the model "
                                           "requested on it overrides --profile")
    followup.set_defaults(func=cmd_followup)

    sub.add_parser("profiles", help="list LLM profiles").set_defaults(func=cmd_profiles)

    conv = sub.add_parser("conversation", help="inspect a conversation")
    conv.add_argument("conversation_id")
    conv.add_argument("--final-response", action="store_true")
    conv.set_defaults(func=cmd_conversation)

    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    args.workspace_id = (args.workspace_id or os.environ.get("VIBE_WORKSPACE_ID")
                         or DEFAULTS.get("workspace_id"))
    args.working_dir = (args.working_dir or os.environ.get("VIBE_WORKSPACE_PATH")
                        or DEFAULTS.get("workspace_path"))

    needs_ws = args.command in ("snapshot", "patch", "dispatch", "followup")
    if needs_ws and not args.workspace_id:
        print(json.dumps({"error": "workspace id required (--workspace-id or "
                                   "VIBE_WORKSPACE_ID)"}), file=sys.stderr)
        return 2
    if args.command in ("dispatch", "followup") and not args.working_dir:
        print(json.dumps({"error": "working dir required (--working-dir or "
                                   "VIBE_WORKSPACE_PATH)"}), file=sys.stderr)
        return 2

    try:
        return args.func(args)
    except (ValueError, KeyError, RuntimeError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
