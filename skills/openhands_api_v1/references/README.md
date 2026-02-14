# OpenHands Cloud API V1 references

This skill intentionally ships a **minimal** client plus a short list of the most useful endpoints.

The V1 app server routes are served from the OpenHands Cloud app host:

- Base URL (default): `https://app.all-hands.dev`
- API prefix: `/api/v1`

Key concepts:

- **App server** endpoints use Bearer auth (`Authorization: Bearer <OPENHANDS_API_KEY>`).
- **Agent server** endpoints are served by the sandbox runtime and use session auth (`X-Session-API-Key`).

If you need deeper, up-to-date definitions, check the OpenHands main repository for the latest server route implementations. In that repo, the V1 app server routes typically live under:

- `openhands/app_server/routes/`

(The legacy V0 API routes live under `openhands/server/routes/`.)
