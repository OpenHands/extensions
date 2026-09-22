# Connecting an OpenHands App

Use the narrowest supported connection surface. Treat backend URLs, session keys, and automation credentials as capabilities supplied by Agent Canvas or a backend, not values to discover from browser globals or guessed ports.

## Prefer the TypeScript client

Prefer [`@openhands/typescript-client`](https://github.com/OpenHands/software-agent-sdk/tree/main/clients/typescript) whenever a bundled TypeScript app has the connection inputs required by the client and the client covers the needed Agent Server API. It provides maintained request models, typed clients, event types, compatibility checks, and WebSocket lifecycle code that track the canonical Agent Server contract.

Use direct `fetch` or raw `WebSocket` only when:

- the client does not yet expose the required endpoint or transport option;
- host API 1 supplies only its narrower request adapter;
- a small dependency-free app does not justify bundling the client; or
- an integration targets the separate Automation service, which the Agent Server client does not model.

Pin a compatible client version, bundle it into the app's self-contained ESM entrypoint, and test the built bundle. Do not leave `@openhands/typescript-client` as a browser bare import or external chunk. Check the current package exports before selecting a client class; the repository evolves with the Agent Server API.

## Agent Server HTTP

For a host API 1 app, use the host-provided authenticated adapter:

```js
const conversations = await host.agentServer.request({
  method: "POST",
  path: "/api/conversations/search",
  body: { limit: 20 },
});
```

Pass exactly one root-relative path. Do not pass an origin, protocol-relative URL, or path without a leading slash. Let Canvas select the active backend and attach its authentication. This preserves backend switching and avoids placing a session key in app code.

Do not construct an `HttpClient` from `host.backend`: host API 1 exposes backend identity (`id`, `kind`, and `orgId`), not an Agent Server origin or session API key. Do not inspect Canvas internals, Redux stores, local storage, DOM attributes, or undocumented globals to recover those values.

When developing a trusted standalone browser client outside Agent Canvas, prefer the TypeScript client:

```ts
import { HttpClient } from "@openhands/typescript-client";

const client = new HttpClient({
  baseUrl: agentServerOrigin,
  apiKey: sessionApiKey,
});

const response = await client.get("/server_info");
```

Supply the actual Agent Server origin, including any reverse-proxy path prefix. The client attaches `X-Session-API-Key` when `apiKey` is set. Consult the live `/openapi.json` and `/server_info` before relying on endpoints that may differ across server versions.

If typed high-level clients cover the operation, prefer those over the generic `HttpClient`. Use the generic client for uncovered Agent Server endpoints, not as a reason to duplicate authentication and error handling with `fetch`.

## Automation backend

Treat the Automation service as a separate backend. Its API is normally mounted under `/api/automation/v1`, but the origin, path prefix, and authentication mode are deployment-provided values rather than Agent Server defaults.

Host API 1 does not expose an automation request helper, automation base URL, or automation credential. Therefore, an app must not:

- route `/api/automation/...` through `host.agentServer.request` unless the owning Agent Server explicitly documents a proxy at that path;
- assume the Automation service shares the Agent Server origin;
- hardcode `localhost`, cloud hosts, or a default API key;
- read ambient Agent Canvas implementation state to obtain private configuration.

Choose one explicit architecture:

1. Add a backend-owned Agent Server endpoint that performs the required automation operation, then call that endpoint through `host.agentServer.request`. Keep automation credentials server-side and scope the proxy to the minimum required operations.
2. Target a future or deployment-specific Canvas host capability that deliberately supplies an authenticated automation request adapter. Feature-detect it and document the required host version.
3. For a separately deployed trusted application, receive the Automation base URL and credential from deployment configuration and call `${automationBaseUrl}/api/automation/v1/...` using that deployment's documented authentication.

Do not use `@openhands/typescript-client` for Automation service routes unless that repository explicitly adds Automation support. The client currently targets Agent Server APIs.

## Agent Server WebSocket

Use WebSocket for live Agent Server events and REST for initial state and writes. Preserve the Agent Server origin's reverse-proxy path prefix when changing `http` to `ws` or `https` to `wss`.

For trusted standalone TypeScript clients, prefer the maintained client:

```ts
import { WebSocketCallbackClient } from "@openhands/typescript-client";

const events = new WebSocketCallbackClient({
  host: agentServerOrigin,
  conversationId,
  apiKey: sessionApiKey,
  callback: (event) => handleEvent(event),
  onError: (error) => showConnectionError(error),
});

events.start();
// Call events.stop() during disposal.
```

The current `WebSocketCallbackClient` appends `session_api_key` to the socket URL when `apiKey` is set. That query-string authentication path remains supported for compatibility, but Agent Server deprecates it because URLs can leak through browser, proxy, or load-balancer logs; the client does not use first-message authentication. For browser sockets against an Agent Server that supports first-message authentication, prefer a raw `WebSocket` until the TypeScript client exposes a first-message-auth option. Use the client only when query-string compatibility is an explicit, acceptable requirement.

Use first-message authentication after opening `/sockets/events/{conversationId}`:

```js
const socket = new WebSocket(eventsUrl);
socket.addEventListener("open", () => {
  socket.send(JSON.stringify({
    type: "auth",
    session_api_key: sessionApiKey,
  }));
});
```

Browsers cannot set arbitrary WebSocket headers. Query-string authentication is a legacy fallback and may leak through URLs or logs; use it only when required by the selected client/server compatibility window.

Host API 1 does not expose an Agent Server origin, session API key, or WebSocket factory. A portable v1 app therefore cannot open an authenticated Agent Server WebSocket directly. Do not derive a socket from `window.location`: Canvas and the active Agent Server may use different origins or proxy prefixes, and backend switching would leave the socket attached to the wrong server.

For live app data under host API 1, choose one of these approaches:

- poll through `host.agentServer.request` with bounded intervals, visibility awareness, abort/disposal guards, and a stale state;
- add a backend endpoint that aggregates the required state and expose it through the authenticated host request adapter; or
- require and feature-detect a future host WebSocket/subscription capability.

Always close sockets, stop TypeScript client instances, clear reconnect timers, and suppress late callbacks when the page unmounts or the app deactivates.

## Testing connection behavior

Test the supported boundary rather than hidden Canvas implementation details:

- assert Agent Server HTTP uses `host.agentServer.request` with a root-relative path;
- assert no session key or backend origin is embedded in the built app;
- assert an unavailable Automation capability produces a clear unsupported state rather than a guessed request;
- assert polling, sockets, and TypeScript client instances stop during disposal;
- assert backend changes cause old connection state to be discarded;
- inspect the final bundle for unresolved client imports and external chunks.
