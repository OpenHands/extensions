"""Exercise the catalog command against the released official MCP server.

Run with Python's mcp package installed and Node.js/npx available:
    python .pr/smoke_azure_devops.py

Uses a synthetic PAT only. initialize and tools/list do not access user data.
"""

import asyncio
import base64
import json
import shutil
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    root = Path(__file__).resolve().parents[1]
    entry = json.loads(
        (root / "integrations/catalog/azure-devops.json").read_text(encoding="utf-8")
    )
    transport = next(
        option["transport"] for option in entry["connectionOptions"]
        if option["id"] == "pat"
    )
    command = shutil.which(transport["command"])
    assert command, "npx is required"
    # Canvas appends argFields to the fixed catalog args. A fixed tenant keeps
    # this credential-free smoke test from querying organization metadata.
    args = [*transport["args"], "contoso", "--tenant", "organizations"]
    credential = base64.b64encode(b"smoke-user:synthetic-pat").decode()
    parameters = StdioServerParameters(
        command=command, args=args, env={"PERSONAL_ACCESS_TOKEN": credential}
    )
    async with asyncio.timeout(90):
        async with stdio_client(parameters) as (read, write):
            async with ClientSession(read, write) as session:
                initialized = await session.initialize()
                tools = await session.list_tools()
                names = {tool.name for tool in tools.tools}
                assert "core_list_projects" in names
                assert any(name.startswith("wit_") for name in names)
                print(json.dumps({
                    "server": initialized.serverInfo.model_dump(),
                    "protocol": initialized.protocolVersion,
                    "tool_count": len(names),
                    "projects_tool": "core_list_projects" in names,
                    "work_item_tools": sorted(n for n in names if n.startswith("wit_")),
                    "authenticated_azure_api_calls": False,
                }, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
