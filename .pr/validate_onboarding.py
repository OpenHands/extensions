"""Install a clean local plugin bundle, load it, trigger and execute its scanners.

Run: uv run --with openhands-sdk==1.49.0 python .pr/validate_onboarding.py
No model, credentials, global configuration or network calls are used here.
"""

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from importlib.metadata import version
from pathlib import Path

from openhands.sdk.plugin import Plugin


ROOT = Path(__file__).resolve().parents[1]
bash = shutil.which("bash")
if os.name == "nt":
    bash = str(Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/bin/bash.exe")


def write(repo, name, content="fixture\n"):
    path = repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def snapshot(repo):
    return {str(p.relative_to(repo)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in repo.rglob("*") if p.is_file()}


results = {"sdk_version": version("openhands-sdk"), "platform": os.name}
with tempfile.TemporaryDirectory(prefix="onboarding e2e ") as temp:
    installed = Path(temp) / "installed/onboarding"
    shutil.copytree(ROOT / "plugins/onboarding", installed, symlinks=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    plugin = Plugin.load(installed)
    assert plugin.name == "onboarding"
    assert len(plugin.skills) == 5
    skill = next(s for s in plugin.skills if s.name == "agent-readiness-report")
    assert "Scanners prune" in skill.content
    positives = ["Run agent-readiness-report", "Give me a readiness report",
                 "READINESS REPORT for this repo", "Use agent-readiness-report on my package",
                 "Refresh the readiness report after dependency installation"]
    negatives = ["Fix this failing unit test", "Install dependencies", "Write a README",
                 "Review the pull request", "What is the weather today?"]
    assert all(skill.match_trigger(p) for p in positives)
    assert all(skill.match_trigger(p) is None for p in negatives)
    results["loading_and_activation"] = {"skills": len(plugin.skills), "positive": 5, "negative": 5}

    repo = Path(temp) / "assessed repo"
    repo.mkdir()
    for excluded in ("node_modules", ".venv", "venv", ".git"):
        for name in ("AGENTS.md", "SECURITY.md", "pull_request_template.md", "test_dependency.py"):
            write(repo, f"{excluded}/pkg/{name}")
        for name in ("Dockerfile", "eslint.config.js"):
            write(repo, f"{excluded}/{name}")
    scripts = installed / "skills/agent-readiness-report/scripts"
    before = snapshot(repo)
    dependency_only = {}
    for script in sorted(scripts.glob("scan_*.sh")):
        result = subprocess.run([bash, script.as_posix(), repo.as_posix()],
                                capture_output=True, text=True, encoding="utf-8", timeout=30)
        assert result.returncode == 0, result.stderr
        assert not result.stderr, result.stderr
        assert not any(f"./{d}/" in result.stdout for d in ("node_modules", ".venv", "venv", ".git"))
        dependency_only[script.name] = {"exit_code": result.returncode, "stdout": result.stdout}
    assert "  0 test files found" in dependency_only["scan_feedback_loops.sh"]["stdout"]
    assert snapshot(repo) == before
    results["dependency_only"] = dependency_only

    expectations = {
        "scan_agent_instructions.sh": "./packages/app/AGENTS.md",
        "scan_feedback_loops.sh": "  1 test files found",
        "scan_workflows.sh": "./.github/pull_request_template.md",
        "scan_policy.sh": "./docs/SECURITY.md",
        "scan_build_env.sh": "./services/Dockerfile",
    }
    for name in ("packages/app/AGENTS.md", "packages/app/tests/test_project.py",
                 ".github/pull_request_template.md", "docs/SECURITY.md", "services/Dockerfile"):
        write(repo, name)
    authored = {}
    for name, expected in expectations.items():
        result = subprocess.run([bash, (scripts / name).as_posix(), repo.as_posix()],
                                capture_output=True, text=True, encoding="utf-8", timeout=30)
        assert result.returncode == 0 and not result.stderr
        assert expected in result.stdout, (name, result.stdout)
        authored[name] = {"exit_code": result.returncode, "evidence": expected}
    results["authored_project"] = authored

    # Exercise the same installed scripts on this real source checkout too.
    checkout = {}
    for script in sorted(scripts.glob("scan_*.sh")):
        result = subprocess.run([bash, script.as_posix(), ROOT.as_posix()],
                                capture_output=True, text=True, encoding="utf-8", timeout=30)
        assert result.returncode == 0 and not result.stderr
        assert "./.venv/" not in result.stdout and "./node_modules/" not in result.stdout
        checkout[script.name] = {"exit_code": result.returncode, "stdout": result.stdout}
    results["real_extensions_checkout"] = checkout
    missing = subprocess.run([bash, (scripts / "scan_feedback_loops.sh").as_posix(),
                              (repo / "missing").as_posix()], capture_output=True, text=True)
    assert missing.returncode == 1 and "Cannot access" in missing.stdout
    results["missing_repository"] = {"exit_code": 1, "message": "Cannot access"}
    del skill, plugin
assert not installed.exists()
results["cleanup"] = "temporary installation removed; assessed files were not modified"
print(json.dumps(results, indent=2))
