"""Read one public catalog entry through the OpenHands MCP client."""

import os
from getpass import getpass
from importlib.metadata import version

import requests
from openhands.sdk.mcp import MCPServer, create_mcp_tools
from openhands_extensions import get_integration_catalog_entry_model


def metadata(path):
    response = requests.get(f"https://treg.to/.well-known/{path}", timeout=15)
    response.raise_for_status()
    return response.json()


entry = get_integration_catalog_entry_model("treg")
oauth, api = entry.connectionOptions
url = api.transport.url
assert url == oauth.transport.url == "https://treg.to/mcp/"
assert oauth.auth.strategy == "oauth2" and api.auth.strategy == "bearer"
resource = metadata("oauth-protected-resource")
issuer = metadata("oauth-authorization-server")
config = oauth.auth.oauth
assert resource["resource"] == url and issuer["issuer"] in resource["authorization_servers"]
assert config.authorizationUrl == issuer["authorization_endpoint"]
assert config.tokenUrl == issuer["token_endpoint"]
assert config.registrationUrl == issuer["registration_endpoint"]
assert set(config.scopes) <= set(resource["scopes_supported"])
assert config.pkce and "S256" in issuer["code_challenge_methods_supported"]
assert config.clientAuthentication in issuer["token_endpoint_auth_methods_supported"]
print("OAuth discovery matched the catalog URL, endpoints, scopes and PKCE.")

token = os.environ.get("TREG_TOKEN") or getpass("Treg team API key: ")
server = MCPServer.model_validate({
    "url": url,
    "transport": "http",
    "auth": {"strategy": api.auth.strategy, "value": token},
})
with create_mcp_tools({entry.id: server}, timeout=30) as client:
    names = {tool.name for tool in client.tools}
    assert {"catalog_search", "catalog_get", "call"} <= names
    print(f"OpenHands SDK {version('openhands-sdk')} connected. Found {len(names)} MCP tools.")
    result = client.call_async_from_sync(
        client.call_tool_mcp,
        name="catalog_get",
        arguments={"endpoint_id": "treg.web.search"},
        timeout=30,
    )
    assert not result.is_error
    endpoint = result.structured_content["endpoint"]
    assert endpoint["id"] == "treg.web.search" and endpoint["method"] == "POST"
    assert endpoint["cost"]["currency"] == "USD"
    print("catalog_get returned treg.web.search, method POST and USD pricing.")
