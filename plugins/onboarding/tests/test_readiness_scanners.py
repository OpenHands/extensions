"""Exercise the shell entrypoints with authored and installed package files."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "skills/agent-readiness-report/scripts"
BASH = shutil.which("bash")
if os.name == "nt":
    # Windows' system bash may be a WSL launcher; use Git Bash for Windows paths.
    git_bash = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/bin/bash.exe"
    BASH = str(git_bash) if git_bash.is_file() else None


@unittest.skipUnless(BASH, "The onboarding scanners require Bash")
class TestReadinessScanners(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="readiness repo ")
        self.addCleanup(self.directory.cleanup)
        self.repo = Path(self.directory.name)

    def write(self, name, content="fixture\n"):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def scan(self, name, repo=None):
        result = subprocess.run(
            [BASH, (SCRIPTS / name).as_posix(), (repo or self.repo).as_posix()],
            capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.returncode, 0, result.stdout)
        return result.stdout

    def test_dependency_tests_do_not_inflate_authored_test_count(self):
        self.write("tests/test_project.py")
        self.write("node_modules/pkg/test_dependency.py")
        self.write(".venv/lib/test_dependency.py")
        output = self.scan("scan_feedback_loops.sh")
        self.assertIn("  1 test files found", output)

    def test_all_scanners_prune_installed_packages_and_git_metadata(self):
        for excluded in ("node_modules", ".venv", "venv", ".git"):
            for name in ("AGENTS.md", "SECURITY.md", "pull_request_template.md"):
                self.write(f"{excluded}/pkg/{name}")
            for name in (".eslintrc.json", "Dockerfile"):
                self.write(f"{excluded}/{name}")
        for script in sorted(SCRIPTS.glob("scan_*.sh")):
            with self.subTest(script=script.name):
                output = self.scan(script.name)
                for excluded in ("node_modules", ".venv", "venv", ".git"):
                    self.assertNotIn(f"./{excluded}/", output)

    def test_nested_dependency_directory_is_pruned(self):
        self.write("packages/web/node_modules/pkg/test_dependency.py")
        self.write("packages/web/tests/test_project.py")
        self.assertIn("  1 test files found", self.scan("scan_feedback_loops.sh"))

    def test_authored_monorepo_instructions_remain_visible(self):
        self.write("packages/web/AGENTS.md")
        self.assertIn("./packages/web/AGENTS.md", self.scan("scan_agent_instructions.sh"))

    def test_authored_policy_workflow_and_build_files_remain_visible(self):
        self.write("docs/security/SECURITY.md")
        self.write(".github/pull_request_template.md")
        self.write("services/Dockerfile")
        self.assertIn("./docs/security/SECURITY.md", self.scan("scan_policy.sh"))
        self.assertIn("./.github/pull_request_template.md", self.scan("scan_workflows.sh"))
        self.assertIn("./services/Dockerfile", self.scan("scan_build_env.sh"))

    def test_authored_linter_config_remains_visible(self):
        self.write("config/eslint.config.js")
        self.assertIn("./config/eslint.config.js", self.scan("scan_feedback_loops.sh"))

    def test_snapshot_and_benchmark_counts_exclude_dependencies(self):
        self.write("node_modules/pkg/__snapshots__/dependency.snap")
        self.write("node_modules/pkg/testdata/data.json")
        self.write("node_modules/pkg/dependency_benchmark.py")
        output = self.scan("scan_feedback_loops.sh")
        self.assertIn("  0 snapshot dirs/files, 0 testdata dirs", output)
        self.assertIn("  0 benchmark files found", output)

    def test_named_test_directories_are_not_test_files(self):
        (self.repo / "test_directory.py").mkdir()
        self.assertIn("  0 test files found", self.scan("scan_feedback_loops.sh"))

    def test_scanning_does_not_write_to_the_assessed_repository(self):
        self.write("tests/test_project.py")
        self.write(".venv/lib/test_dependency.py")
        before = {p.relative_to(self.repo): p.read_bytes() for p in self.repo.rglob("*") if p.is_file()}
        for script in sorted(SCRIPTS.glob("scan_*.sh")):
            self.scan(script.name)
        after = {p.relative_to(self.repo): p.read_bytes() for p in self.repo.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_missing_repository_is_an_error(self):
        result = subprocess.run(
            [BASH, (SCRIPTS / "scan_feedback_loops.sh").as_posix(), (self.repo / "missing").as_posix()],
            capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Cannot access", result.stdout)

        # Copying just an entrypoint must fail instead of reporting empty scans.
        standalone = self.repo / "scan_feedback_loops.sh"
        shutil.copyfile(SCRIPTS / standalone.name, standalone)
        missing_helper = subprocess.run(
            [BASH, standalone.as_posix(), self.repo.as_posix()],
            capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
        self.assertEqual(missing_helper.returncode, 1)
        self.assertIn("find_repo.sh", missing_helper.stderr)


if __name__ == "__main__":
    unittest.main()
