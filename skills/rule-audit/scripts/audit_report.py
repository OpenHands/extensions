#!/usr/bin/env python3
"""Bounded rule-audit report for the Claude Code `/rule-audit:audit` command.

This is a thin adapter over the installed `rule-audit` CLI. It adds nothing to
detection and decides nothing about severity: it shells out to
`rule-audit --file=PATH --format json`, then prints a size-bounded rendering of
what came back and re-raises the CLI's own exit code.

Why an adapter script rather than letting the model compose the command:

* **Bounded output.** A real prompt file can produce thousands of findings
  (measured: 1,875 contradictions from a single 124-rule document). Piping that
  into an agent's context is not useful. This caps every family and always
  prints the exact command to see the rest. The bound is applied to the
  analyzer's output *while the analyzer runs*, not to a buffer this process has
  already paid for in full: the JSON behind a 4 KB report has been measured at
  318 MB. See `MAX_OUTPUT_BYTES`.
* **Bounded input.** `rule_audit.audit` is O(n^2) in parsed rules with no size
  guard of its own. Large inputs are refused with an actionable message rather
  than stalling the session. See `MAX_INPUT_BYTES`.
* **A named runtime.** `rule-audit` on `PATH` is frequently an older release
  than the one a project expects. This resolves a runtime that meets
  `MIN_VERSION` and prints the version it actually used.
* **Determinism.** `generated_at` is never read, so two runs over unchanged
  input produce byte-identical output.

Exit codes are the CLI's, unchanged: 0 = LOW/MEDIUM, 2 = HIGH/CRITICAL,
1 = the audit could not be run.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

#: Minimum rule-audit release this adapter is written against. 0.3.1 is the
#: first release whose calibration corpus ships inside the wheel.
MIN_VERSION = (0, 3, 1)

#: Refuse inputs above this size. rule-audit's contradiction pass is O(n^2) in
#: parsed rules and the package applies no cap of its own; measured on this
#: adapter's own fixtures, 64 KB of dense rule text is a few seconds while
#: 248 KB is ~54 s and several GB of resident memory. A prompt file this large
#: is better audited deliberately than from inside an interactive session.
MAX_INPUT_BYTES = 64 * 1024

#: Hard ceiling on what the analyzer may hand back on stdout, enforced while
#: the pipe is being read rather than after it has all arrived. Bounding the
#: input does not bound the report: measured on this adapter's own fixtures,
#: all inside the 64 KB input cap, a 50 KB documentation file yields 1.0 MB of
#: JSON, a 16 KB file of dense imperative rules yields 23 MB (143 MB resident),
#: and a 64 KB one — the largest input this adapter accepts, and exactly the
#: shape rule-audit is calibrated for — yields 318 MB and peaks at 1.8 GB
#: resident to render the same 4 KB of Markdown. 32 MB is ~32x the largest
#: realistic report measured and holds the parse to roughly 200 MB.
MAX_OUTPUT_BYTES = 32 * 1024 * 1024

#: Hard ceiling on analyzer stderr, which is quoted back inside the failure
#: messages below. Without it the buffer that explains why an audit failed
#: could be the thing that exhausts memory — the failure path has to be bounded
#: for the same reason the success path does.
MAX_STDERR_BYTES = 64 * 1024

#: Wall-clock ceiling for the analyzer itself. `codex_audit.py` sets a shorter
#: one around this whole process; this is the backstop when the adapter is run
#: directly.
ANALYZER_TIMEOUT_SECONDS = 120

#: Read size for the bounded reads. Large enough not to read a multi-megabyte
#: report a syscall at a time, small enough that passing a cap is noticed
#: within one read of it happening.
_READ_CHUNK_BYTES = 64 * 1024

#: Granularity of the wait loop. Exceeding a cap is signalled through an event,
#: so this paces only the check for *normal* completion: milliseconds against
#: an audit measured in seconds.
_POLL_SECONDS = 0.02

#: Backstop for collecting the drained pipes and the exit status once the
#: analyzer has finished or been killed. Both are already over by then.
_DRAIN_SECONDS = 10

#: Per-family cap on rendered findings. The counts above the table are always
#: the true totals; only the listing is truncated.
MAX_ROWS_PER_FAMILY = 5

#: Cap on any single quoted span of prompt text.
MAX_QUOTE_CHARS = 160

_FAMILIES: Sequence[Tuple[str, str]] = (
    ("contradictions", "Contradictions"),
    ("priority_ambiguities", "Priority ambiguities"),
    ("meta_paradoxes", "Meta-paradoxes"),
    ("absoluteness_issues", "Absoluteness issues"),
    ("gaps", "Coverage gaps"),
)


#: Control characters, including the newlines that would let untrusted text
#: open a new Markdown block. Unix filenames and prompt bodies may contain any
#: of these.
_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def _quote(value: Any) -> str:
    """One-line, length-capped rendering of prompt-derived text.

    Collapsing whitespace is what keeps untrusted text inside the bullet it was
    rendered into: without it, a rule containing a newline followed by `#` would
    open a heading in a report the model is asked to read and act on.
    """
    # `str(value or "")` would be wrong here: rule indexes are ints and the
    # first rule in every report is index 0, which is falsy, so the citation
    # rendered as `rule []` and the reader could not tell which rule was meant.
    text = "" if value is None else str(value)
    text = " ".join(_CONTROL.sub(" ", text).split())
    if len(text) > MAX_QUOTE_CHARS:
        text = text[: MAX_QUOTE_CHARS - 1] + "…"
    return text


#: Inline Markdown and HTML delimiters. Block constructs need a newline, which
#: `_quote` already removes, so containing the inline set is sufficient.
_MARKDOWN = re.compile(r"([\\`*_\[\]<>|~])")


def _text(value: Any) -> str:
    """Render text that is mostly the analyzer's own words but embeds the prompt's.

    Several descriptions interpolate rule text verbatim — `analyzer.py` builds
    scope-conflict descriptions from `rule.text[:80]` and potential-override
    descriptions the same way — so a prompt containing backticks, emphasis or a
    raw HTML tag would otherwise style a report the model is asked to act on.
    Escaping rather than fencing keeps the analyzer's sentence readable.
    """
    return _MARKDOWN.sub(r"\\\1", _quote(value))


def _code(value: Any) -> str:
    """Render untrusted text as inline code it cannot break out of.

    Per CommonMark, a code span delimited by N backticks can contain any run of
    fewer than N backticks, so the fence is chosen to be longer than the longest
    run in the text. Used for the audited path and for prompt text quoted back
    verbatim — both are attacker-controllable when the audited file is.
    """
    text = _quote(value)
    if not text:
        return "``` ```"
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    fence = "`" * (longest + 1)
    pad = " " if text.startswith("`") or text.endswith("`") else ""
    return "%s%s%s%s%s" % (fence, pad, text, pad, fence)


def _parse_version(text: str) -> Optional[Tuple[int, ...]]:
    """Extract a dotted numeric version from `rule-audit X.Y.Z` output."""
    for token in text.split():
        parts = token.split(".")
        if len(parts) >= 2 and all(part.isdigit() for part in parts):
            return tuple(int(part) for part in parts)
    return None


def _probe(command: List[str]) -> Optional[Tuple[int, ...]]:
    """Return the version `command` reports, or None if it is unusable."""
    try:
        completed = subprocess.run(
            command + ["--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    return _parse_version(completed.stdout or "")


def _candidates() -> List[List[str]]:
    """Runtimes to try, best first.

    `RULE_AUDIT_PYTHON` lets a project point at the interpreter of a virtualenv
    that has rule-audit installed, which is the common case when the version on
    `PATH` is older than the project needs.
    """
    found: List[List[str]] = []
    override = os.environ.get("RULE_AUDIT_PYTHON")
    if override:
        found.append([override, "-m", "rule_audit"])
    found.append([sys.executable, "-m", "rule_audit"])
    for name in ("python3", "python"):
        path = shutil.which(name)
        if path and path != sys.executable:
            found.append([path, "-m", "rule_audit"])
    executable = shutil.which("rule-audit")
    if executable:
        found.append([executable])
    return found


def resolve_runtime() -> Tuple[Optional[List[str]], List[str]]:
    """Find a rule-audit that meets MIN_VERSION.

    Returns (command, rejections). `rejections` records what was found and why
    it was not used, so the failure message can name the real problem — usually
    "installed, but too old" rather than "not installed".
    """
    rejections: List[str] = []
    for command in _candidates():
        version = _probe(command)
        if version is None:
            continue
        if version >= MIN_VERSION:
            return command, rejections
        rejections.append(
            "%s reports %s (needs %s or newer)"
            % (
                " ".join(command),
                ".".join(str(part) for part in version),
                ".".join(str(part) for part in MIN_VERSION),
            )
        )
    return None, rejections


def _render(path: str, data: Dict[str, Any], version_note: str) -> str:
    """Render the audit as bounded Markdown. Never reads `generated_at`."""
    rule_count = data.get("rule_count", 0)
    risk_label = data.get("risk_label", "UNKNOWN")
    risk_score = data.get("risk_score", 0.0)

    lines = [
        # The path is attacker-controlled whenever the audited file is: a
        # filename may contain newlines and Markdown, and this report is read
        # by a model. Render it as inline code, never as bare heading text.
        "# rule-audit — %s" % _code(path),
        "",
        "%s | %d rules parsed | risk %s (%.0f/100)"
        % (version_note, rule_count, risk_label, risk_score),
        "",
    ]

    if rule_count == 0:
        lines += [
            "**No rules were parsed from this file.** Nothing was checked, so this "
            "result says nothing about the file's content. The coverage gaps below "
            "are reported against an empty rule set.",
            "",
        ]

    counts = {key: len(data.get(key) or []) for key, _ in _FAMILIES}
    lines.append(
        "| Finding family | Count |\n|---|---|\n"
        + "\n".join(
            "| %s | %d |" % (title, counts[key]) for key, title in _FAMILIES
        )
    )
    lines.append("")

    for key, title in _FAMILIES:
        items = data.get(key) or []
        if not items:
            continue
        lines.append("## %s (%d)" % (title, len(items)))
        lines.append("")
        for item in items[:MAX_ROWS_PER_FAMILY]:
            lines.extend(_render_item(key, item))
        if len(items) > MAX_ROWS_PER_FAMILY:
            lines.append(
                "- … and %d more not shown."
                % (len(items) - MAX_ROWS_PER_FAMILY)
            )
        lines.append("")

    lines += [
        "---",
        "",
        "`%s` is a lexical score, not a proven exploit: it means "
        '"this many absolute rules and detected conflicts for a document this '
        'size". rule-audit parses with sentence splitting and modal-verb regexes, '
        "so it both misses rules that need semantic reading and pairs unrelated "
        "rules that share a keyword. Read each finding before acting on it."
        % risk_label,
        "",
        "Full report, nothing truncated:",
        "",
    ]
    lines.extend(_command_block(path))
    return "\n".join(lines)


def _cli_arguments(path: str) -> List[str]:
    """Arguments handed to the rule-audit CLI for `path`.

    The equals form is what makes a dash-prefixed basename a filename: given
    `--file -x`, argparse reads `-x` as another option and reports that
    `--file` is missing its argument. The printed commands use the same form
    for the same reason, so what the user pastes is what ran.
    """
    return ["--file=%s" % path, "--format", "json"]


def _command_block(path: str) -> List[str]:
    """The copy-pasteable full-report commands, when the path can carry them.

    A control character in the filename would either break out of the fence or
    make the printed command silently different from the one that runs, so in
    that case say so rather than print something untrue.
    """
    if _CONTROL.search(path):
        return [
            "The filename contains control characters, so the exact command "
            "cannot be shown here. Run `rule-audit --file=PATH` against it "
            "directly for the untruncated report.",
        ]
    return [
        "```bash",
        "rule-audit --file=%s" % _shell_quote(path),
        "rule-audit --file=%s --min-severity high" % _shell_quote(path),
        "```",
    ]


def _render_item(key: str, item: Dict[str, Any]) -> List[str]:
    """One bullet per finding, using only fields the CLI already emits.

    Text taken verbatim from the audited prompt is rendered as inline code, both
    so it cannot restyle the report and so the reader can see where the tool's
    words end and the prompt's begin.
    """
    if key == "contradictions":
        return [
            "- **%s / %s** — %s"
            % (
                _text(item.get("conflict_type", "?")),
                _text(item.get("severity", "?")),
                _text(item.get("description")),
            ),
            "  - rule [%s]: %s"
            % (_text(item.get("rule_a_index", "?")), _code(item.get("rule_a_text"))),
            "  - rule [%s]: %s"
            % (_text(item.get("rule_b_index", "?")), _code(item.get("rule_b_text"))),
        ]
    if key == "priority_ambiguities":
        return ["- %s" % _text(item.get("description"))]
    if key == "meta_paradoxes":
        return [
            "- **%s** — %s"
            % (
                _text(item.get("paradox_type", "?")),
                _text(item.get("description")),
            ),
            "  - rule [%s]: %s"
            % (_text(item.get("rule_index", "?")), _code(item.get("rule_text"))),
        ]
    if key == "absoluteness_issues":
        return [
            "- **%s** — %s"
            % (
                _text(item.get("challenge_type", "?")),
                _text(item.get("challenge")),
            ),
            "  - rule [%s]: %s"
            % (_text(item.get("rule_index", "?")), _code(item.get("rule_text"))),
        ]
    return [
        "- **%s** — %s"
        % (_text(item.get("gap_type", "?")), _text(item.get("description")))
    ]


def _shell_quote(path: str) -> str:
    if path and all(char.isalnum() or char in "./_-" for char in path):
        return path
    return "'%s'" % path.replace("'", "'\\''")


class _ArgumentParser(argparse.ArgumentParser):
    """ArgumentParser whose usage errors exit 1, not argparse's default 2.

    2 is the HIGH/CRITICAL exit code this adapter re-raises, so a usage error
    must not share it: a dash-prefixed path passed without `--` would
    otherwise read as a finding.
    """

    def error(self, message: str) -> None:  # type: ignore[override]
        self.print_usage(sys.stderr)
        self.exit(1, "%s: error: %s\n" % (self.prog, message))


def _fail(message: str) -> int:
    # Failure messages embed the path and the CLI's stderr, both of which can
    # carry control characters from an untrusted filename or file. Keep them to
    # the single line they are presented as.
    sys.stderr.write("rule-audit: %s\n" % _CONTROL.sub(" ", message))
    return 1


def _snapshot_input(path: str) -> Tuple[Optional[str], Optional[str]]:
    """Copy one bounded, regular-file snapshot and return its path or an error.

    Opening the source once binds the size check and the audited bytes to the
    same file even if the pathname is replaced concurrently. O_NONBLOCK keeps
    a FIFO from hanging before fstat can reject it.
    """
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0)
    source_fd = -1
    try:
        source_fd = os.open(path, flags)
        metadata = os.fstat(source_fd)
        if stat.S_ISDIR(metadata.st_mode):
            return None, "%r is a directory; pass a single prompt file." % path
        if not stat.S_ISREG(metadata.st_mode):
            return None, "%r is not a regular file; pass a single prompt file." % path
        with os.fdopen(source_fd, "rb") as source:
            source_fd = -1
            content = source.read(MAX_INPUT_BYTES + 1)
    except FileNotFoundError:
        return None, "file not found: %s" % path
    except PermissionError:
        return None, "permission denied reading %s" % path
    except OSError as error:
        return None, "could not read %s: %s" % (path, error)
    finally:
        if source_fd >= 0:
            os.close(source_fd)

    if len(content) > MAX_INPUT_BYTES:
        measured_size = max(metadata.st_size, len(content))
        return None, (
            "%s is %d bytes; this command audits files up to %d bytes because "
            "rule-audit's contradiction pass is O(n^2) in parsed rules. Run "
            "`rule-audit --file=%s` directly to audit it anyway."
            % (path, measured_size, MAX_INPUT_BYTES, _shell_quote(path))
        )

    snapshot_fd = -1
    snapshot_path: Optional[str] = None
    try:
        snapshot_fd, snapshot_path = tempfile.mkstemp(prefix="rule-audit-", suffix=".txt")
        with os.fdopen(snapshot_fd, "wb") as snapshot:
            snapshot_fd = -1
            snapshot.write(content)
    except OSError as error:
        if snapshot_fd >= 0:
            os.close(snapshot_fd)
        if snapshot_path is not None:
            try:
                os.unlink(snapshot_path)
            except OSError:
                pass
        return None, "could not create a bounded input snapshot: %s" % error
    return snapshot_path, None


def _decode(raw: bytes) -> str:
    """Decode analyzer output that was deliberately read as bytes.

    `text=True` would hand back `str` and leave the cap counting characters,
    which is not a bound on anything a pipe carries. Decoding here instead
    keeps the bound in bytes. The CLI writes its report with `json.dumps`
    defaults, which is ASCII, and ASCII is UTF-8; stderr is a human message
    where a replaced byte is better than an exception raised somewhere it
    cannot be explained. The newline translation is the one `text=True` did.
    """
    return raw.decode("utf-8", "replace").replace("\r\n", "\n")


class _BoundedPipeReader(threading.Thread):
    """Drain one pipe, keeping at most `limit` bytes of what comes out of it.

    Two properties matter here and neither survives `subprocess.run`. What is
    retained is bounded whatever the child writes, because the excess is
    dropped as it arrives rather than buffered whole and sliced afterwards.
    And the pipe goes on being drained past the cap: an unread pipe blocks its
    writer inside the kernel, and a child blocked on a full pipe cannot be
    observed to have exceeded anything, cannot be waited on, and would turn
    this into the stall it exists to prevent.

    `overflowed` is latched from the number of bytes *produced*, not derived
    from the number kept: producing exactly `limit` bytes and producing more
    than `limit` are different facts, and only the second is a failure.
    """

    def __init__(
        self,
        stream: Any,
        limit: int,
        signal_event: Optional[threading.Event] = None,
    ) -> None:
        super().__init__(daemon=True)
        self._stream = stream
        self._signal = signal_event
        self._chunks: List[bytes] = []
        self._kept = 0
        self.limit = limit
        self.produced = 0
        self.overflowed = False

    def run(self) -> None:
        # `read1` returns as soon as anything is available, so a cap is noticed
        # when it is passed rather than when a whole chunk has arrived.
        read = getattr(self._stream, "read1", None) or self._stream.read
        try:
            while True:
                chunk = read(_READ_CHUNK_BYTES)
                if not chunk:
                    break
                self.produced += len(chunk)
                room = self.limit - self._kept
                if room > 0:
                    self._chunks.append(chunk[:room])
                    self._kept += min(room, len(chunk))
                if self.produced > self.limit and not self.overflowed:
                    self.overflowed = True
                    if self._signal is not None:
                        self._signal.set()
        except (OSError, ValueError):
            # The pipe went away under the read — the kill below closed it, or
            # the child exited between the read and the close. What was read
            # before that is what there is.
            pass
        finally:
            try:
                self._stream.close()
            except (OSError, ValueError):
                pass

    def value(self) -> bytes:
        return b"".join(self._chunks)


def _terminate_analyzer(process: "subprocess.Popen[bytes]") -> None:
    """Stop the analyzer, and anything under it, as promptly as the platform allows.

    The analyzer is a direct child — `rule-audit`, or a Python running
    `-m rule_audit` — and it starts nothing itself, so on POSIX signalling the
    child is signalling the tree. It is deliberately not given a session of its
    own: `codex_audit.py` bounds the whole turn by killing the process group it
    puts this process into, and an analyzer that had left that group would
    survive exactly the kill meant to stop it — the defect
    `tests/test_codex_plugin.py` pins for the wrapper. On Windows there is no
    process group to inherit, so `taskkill /F /T` walks the child tree by PID,
    which also covers a runtime that does spawn.
    """
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
        except (OSError, subprocess.SubprocessError):
            pass
    try:
        process.kill()
    except OSError:
        # Already gone, and that is the good case: `ProcessLookupError` is an
        # `OSError`, and there is nothing left to stop.
        pass


def _run_analyzer(
    command: List[str], snapshot_path: str, display_path: str
) -> Tuple[Optional["subprocess.CompletedProcess[str]"], Optional[str]]:
    """Run the analyzer under a hard byte bound on what it can hand back.

    `subprocess.run` cannot express this. It buffers the whole of stdout in
    this process and only then returns, so every cap applied afterwards is a
    cap on something already paid for in full. That is not academic: the report
    is bounded by construction at five findings per family, but the JSON it is
    rendered from is bounded by nothing, and at the input cap it has been
    measured at 318 MB and 1.8 GB resident. See `MAX_OUTPUT_BYTES`.

    Exceeding either cap stops the analyzer rather than merely truncating what
    is kept — a truncated buffer is not a bound on a process that goes on
    writing — and is reported as a failure with the untruncated command to run
    instead. Returns `(completed, None)` when the analyzer finished inside the
    bounds and `(None, message)` when it did not.
    """
    try:
        process = subprocess.Popen(
            command + _cli_arguments(snapshot_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return None, "could not run %s: %s" % (" ".join(command), error)

    exceeded = threading.Event()
    readers = (
        ("stdout", _BoundedPipeReader(process.stdout, MAX_OUTPUT_BYTES, exceeded)),
        ("stderr", _BoundedPipeReader(process.stderr, MAX_STDERR_BYTES, exceeded)),
    )
    for _, reader in readers:
        reader.start()

    deadline = time.monotonic() + ANALYZER_TIMEOUT_SECONDS
    timed_out = False
    while True:
        if exceeded.is_set() or process.poll() is not None:
            break
        if time.monotonic() >= deadline:
            timed_out = True
            break
        # Waiting on the event rather than sleeping is what makes the kill
        # prompt: a reader sets it the moment its cap is passed.
        exceeded.wait(_POLL_SECONDS)

    if timed_out or exceeded.is_set():
        _terminate_analyzer(process)
    # The writer is dead or being killed, so both pipes reach EOF and both
    # readers end; the window is a backstop, not a budget.
    for _, reader in readers:
        reader.join(_DRAIN_SECONDS)
    try:
        process.wait(timeout=_DRAIN_SECONDS)
    except subprocess.TimeoutExpired:  # pragma: no cover - defensive
        pass

    # Read the flags again after the join rather than trusting the loop's view
    # of them: an analyzer that writes past a cap and exits immediately can be
    # seen to have exited first, and those bytes are still an overflow.
    for name, reader in readers:
        if reader.overflowed:
            return None, (
                "the audit of %s was stopped: %s wrote more than %d bytes to "
                "%s, which is more than this command will hold. Run "
                "`rule-audit --file=%s` directly to audit it anyway."
                % (
                    display_path,
                    " ".join(command),
                    reader.limit,
                    name,
                    _shell_quote(display_path),
                )
            )
    if timed_out:
        return None, "audit of %s timed out after %ds." % (
            display_path,
            ANALYZER_TIMEOUT_SECONDS,
        )

    return (
        subprocess.CompletedProcess(
            process.args,
            process.returncode,
            stdout=_decode(readers[0][1].value()),
            stderr=_decode(readers[1][1].value()),
        ),
        None,
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = _ArgumentParser(
        prog="audit_report.py",
        description="Run rule-audit on one prompt file and print a bounded report.",
    )
    parser.add_argument(
        "path",
        help="Path to the prompt file to audit. Put `--` before it if it starts with `-`.",
    )
    args = parser.parse_args(argv)
    path = args.path

    snapshot_path, input_error = _snapshot_input(path)
    if input_error is not None:
        return _fail(input_error)
    assert snapshot_path is not None

    command, rejections = resolve_runtime()
    if command is None:
        try:
            os.unlink(snapshot_path)
        except OSError:
            pass
        detail = ("Found: " + "; ".join(rejections) + ". ") if rejections else ""
        return _fail(
            "no rule-audit %s or newer available. %s"
            "Install it with `pipx install 'rule-audit>=%s'`, or set "
            "RULE_AUDIT_PYTHON to a Python that has it."
            % (
                ".".join(str(part) for part in MIN_VERSION),
                detail,
                ".".join(str(part) for part in MIN_VERSION),
            )
        )

    try:
        completed, failure = _run_analyzer(command, snapshot_path, path)
    finally:
        try:
            os.unlink(snapshot_path)
        except OSError:
            pass
    if failure is not None:
        return _fail(failure)
    assert completed is not None

    if completed.returncode == 1:
        return _fail((completed.stderr or "the audit failed.").strip())

    try:
        data = json.loads(completed.stdout)
    except (ValueError, TypeError):
        return _fail(
            "%s did not return JSON. stderr: %s"
            % (" ".join(command), (completed.stderr or "").strip()[:400])
        )
    if not isinstance(data, dict):
        return _fail("%s returned JSON that is not an object." % " ".join(command))

    version = _probe(command)
    version_note = "rule-audit %s" % (
        ".".join(str(part) for part in version) if version else "unknown version"
    )
    sys.stdout.write(_render(path, data, version_note) + "\n")

    # The CLI's contract, re-raised unchanged: 2 for HIGH/CRITICAL, else 0.
    return 2 if completed.returncode == 2 else 0


if __name__ == "__main__":
    raise SystemExit(main())
