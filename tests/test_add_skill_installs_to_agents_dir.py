from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_fetch_skill_module():
    repo_root = Path(__file__).resolve().parents[1]
    module_path = repo_root / 'skills' / 'add-skill' / 'scripts' / 'fetch_skill.py'
    spec = importlib.util.spec_from_file_location('fetch_skill', module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fetch_skill_installs_into_agents_skills_dir(tmp_path: Path, monkeypatch):
    fetch_skill_mod = _load_fetch_skill_module()
    fetch_skill = fetch_skill_mod.fetch_skill
    monkeypatch.setattr('subprocess.run', lambda *args, **kwargs: None)

    skill_path = 'skills/example-skill'
    src_skill_dir = tmp_path / skill_path
    src_skill_dir.mkdir(parents=True)
    (src_skill_dir / 'SKILL.md').write_text('# Example skill\n')

    class _FakeTempDir:
        def __enter__(self):
            return str(tmp_path)

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr('tempfile.TemporaryDirectory', lambda: _FakeTempDir())

    workspace = tmp_path / 'workspace'
    workspace.mkdir()

    installed_path = Path(fetch_skill('OpenHands/extensions/' + skill_path, str(workspace), force=True))

    assert installed_path == workspace / '.agents' / 'skills' / 'example-skill'
    assert (installed_path / 'SKILL.md').exists()
