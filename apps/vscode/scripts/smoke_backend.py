"""Install the packaged app and start its checksum-pinned official backend."""

import asyncio
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx

from openhands.agent_server.canvas_extensions.backend import CanvasExtensionBackendManager
from openhands.agent_server.canvas_extensions.installed import install_canvas_extension


async def main(source: Path) -> None:
    with TemporaryDirectory(prefix="vscode-app-smoke-") as temporary:
        root = Path(temporary)
        installed = root / "installed"
        install_canvas_extension(str(source.resolve()), installed_dir=installed)
        manager = CanvasExtensionBackendManager(installed, root / "state")
        try:
            revision = manager.revision("vscode")
            assert revision is not None
            prepared = await manager.prepare("vscode", revision)
            assert prepared.prepared_revision == revision, prepared
            started = await manager.start("vscode", revision)
            logs = await manager.logs("vscode", 8192)
            assert started.state == "ready", (started, logs.logs)
            assert manager.ready_endpoint("vscode") == ("127.0.0.1", started.port)
            async with httpx.AsyncClient(trust_env=False) as client:
                response = await client.get(f"http://127.0.0.1:{started.port}/")
                assert response.status_code == 200, response.text[:500]
                assert "workbench" in response.text.lower(), response.text[:500]
            marker = manager.data_dir / "vscode" / "persistence-check"
            marker.write_text("survives restart")
            assert (await manager.stop("vscode")).state == "stopped"
            assert manager.ready_endpoint("vscode") is None
            restarted = await manager.start("vscode", revision)
            assert restarted.state == "ready", restarted
            assert marker.read_text() == "survives restart"
            print(f"Official {manager.current_platform()} artifact: prepare, HTTP editor, stop, restart passed")
        finally:
            await manager.shutdown()


if __name__ == "__main__":
    asyncio.run(main(Path(sys.argv[1])))
