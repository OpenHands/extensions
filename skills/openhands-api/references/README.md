# OpenHands Cloud API references

This skill ships a minimal client plus a short list of the most useful endpoints.

The V1 app server routes are served from the OpenHands Cloud app host:

- Base URL (default): `https://app.all-hands.dev`
- API prefix: `/api/v1`

Key concepts:

- **App server** endpoints use Bearer auth (`Authorization: Bearer <OPENHANDS_CLOUD_API_KEY>`).
- **Agent server** endpoints are served by the sandbox runtime and use session auth (`X-Session-API-Key`).

## Official docs

- https://docs.openhands.dev/openhands/usage/cloud/cloud-api
- https://docs.openhands.dev/openhands/usage/api/v1

## Implementation source of truth

If you need deeper, up-to-date definitions, prefer the current app-server implementation in `OpenHands/OpenHands`:

- `openhands/app_server/v1_router.py`
- `openhands/app_server/app_conversation/app_conversation_router.py`
- `openhands/app_server/app_conversation/app_conversation_models.py`

For the authored docs source, see `OpenHands/docs`:

- `openhands/usage/cloud/cloud-api.mdx`
- `openhands/usage/api/v1.mdx`

(The legacy V0 API routes still live under `openhands/server/routes/`, but new integrations should use V1.)
