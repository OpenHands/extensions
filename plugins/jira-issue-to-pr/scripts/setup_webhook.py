"""
Set up the Jira Cloud webhook of an event-based Jira automation.

Registers a custom webhook source in OpenHands and the matching admin webhook in
Jira Cloud. The two share a signing secret that is generated or rotated here and is
never printed, so it does not enter the conversation. A webhook that already exists
on both sides is updated in place and keeps its secret.

Usage:
  python3 setup_webhook.py apply  --jira-base-url URL --jira-email EMAIL --openhands-host HOST
  python3 setup_webhook.py delete --jira-base-url URL --jira-email EMAIL --openhands-host HOST

  --jira-token-env NAME  environment variable holding the Jira API token (default JIRA_CLOUD_KEY)
  --source NAME          OpenHands webhook source (default "jira")
  --label LABEL          Jira label the webhook is limited to (default "create-pr")
  --jql JQL              JQL filter to use instead of the label
  --name NAME            name of the webhook in Jira
  --dry-run              apply only: report what would change, change nothing
  --rotate-secret        apply only: give an existing pair a new signing secret; without
                         it a webhook that exists on both sides keeps the one it has

Environment:
  OPENHANDS_API_KEY      API key for the OpenHands deployment
  <--jira-token-env>     API token of an account with the Administer Jira permission

Exit codes: 0 done, 1 failed, 2 bad arguments or environment, 3 the Jira account is
not an administrator (set the webhook up by hand instead).
"""
import argparse, base64, hashlib, hmac, json, os, secrets, sys, urllib.error, urllib.parse, urllib.request

JIRA_EVENTS = ["jira:issue_created", "jira:issue_updated"]
# What Jira Cloud sends: the event name in `webhookEvent`, the signature in
# `X-Hub-Signature` as "sha256=<hex HMAC-SHA256 of the body>".
OPENHANDS_WEBHOOK = {
    "event_key_expr": "webhookEvent",
    "signature_header": "X-Hub-Signature",
    "signature_scheme": "hmac_sha256_hex",
}
# No automation listens for this event name, so the signed check starts no run.
CHECK_EVENT = "openhands:setup_check"

_secret = ""


class Failure(Exception):
    def __init__(self, message, code=1):
        super().__init__(message)
        self.code = code


def _redact(text):
    return text.replace(_secret, "***") if _secret else text


def _call(method, url, headers, body=None):
    """Return (status, parsed JSON or text). An HTTP error status is returned, not raised."""
    data = json.dumps(body).encode() if body is not None else None
    if data is not None:
        headers = {**headers, "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            status, raw = resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        status, raw = exc.code, exc.read()
    except urllib.error.URLError as exc:
        raise Failure(f"{method} {url} failed: {exc.reason}") from exc
    text = raw.decode("utf-8", errors="replace")
    try:
        return status, json.loads(text) if text.strip() else {}
    except ValueError:
        return status, text


def _expect(what, status, body, ok=(200, 201, 204)):
    if status not in ok:
        raise Failure(f"{what} failed: HTTP {status} {_redact(str(body))[:300]}")
    return body


class OpenHands:
    def __init__(self, host, api_key, source):
        self.base = host.rstrip("/") + "/api/automation/v1/webhooks"
        self.headers = {"Authorization": f"Bearer {api_key}"}
        self.source = source

    def find(self):
        status, body = _call("GET", f"{self.base}?limit=100", self.headers)
        webhooks = _expect("Listing OpenHands webhooks", status, body).get("webhooks", [])
        return next((w for w in webhooks if w.get("source") == self.source), None)

    def create(self, secret):
        payload = {"name": "Jira Cloud", "source": self.source, "webhook_secret": secret,
                   **OPENHANDS_WEBHOOK}
        status, body = _call("POST", self.base, self.headers, payload)
        return _expect("Registering the OpenHands webhook", status, body)

    def align(self, webhook):
        """Give an existing webhook the settings Jira needs; return it."""
        wanted = {**OPENHANDS_WEBHOOK, "enabled": True}
        if all(webhook.get(k) == v for k, v in wanted.items()):
            return webhook
        status, body = _call("PATCH", f"{self.base}/{webhook['id']}", self.headers, wanted)
        return _expect("Updating the OpenHands webhook", status, body)

    def rotate(self, webhook):
        status, body = _call("POST", f"{self.base}/{webhook['id']}/rotate-secret", self.headers)
        if status != 200 or not isinstance(body, dict) or not body.get("webhook_secret"):
            raise Failure(f"Rotating the OpenHands webhook secret failed: HTTP {status}")
        return body["webhook_secret"]


class Jira:
    def __init__(self, base_url, email, token):
        self.site = base_url.rstrip("/")
        self.base = self.site + "/rest/webhooks/1.0/webhook"
        basic = base64.b64encode(f"{email}:{token}".encode()).decode()
        self.headers = {"Authorization": f"Basic {basic}", "Accept": "application/json"}

    def require_admin(self):
        status, body = _call(
            "GET", f"{self.site}/rest/api/3/mypermissions?permissions=ADMINISTER", self.headers
        )
        if status in (401, 403):
            raise Failure(f"Jira rejected the credentials (HTTP {status}). Check the site URL, "
                          "the account email and the API token.")
        body = _expect("Reading Jira permissions", status, body)
        try:
            permission = body["permissions"]["ADMINISTER"]
        except (KeyError, TypeError) as exc:
            raise Failure("Reading Jira permissions returned an unexpected response.") from exc
        if not permission.get("havePermission"):
            raise Failure("This Jira account does not have the Administer Jira permission, "
                          "which registering a webhook requires. Ask a Jira administrator to "
                          "create the webhook by hand.", code=3)

    def find(self, url):
        """The webhooks delivering to `url`; none when no URL is known yet."""
        status, body = _call("GET", self.base, self.headers)
        hooks = _expect("Listing Jira webhooks", status, body)
        if not isinstance(hooks, list):
            raise Failure("Listing Jira webhooks returned an unexpected response.")
        return [h for h in hooks if url and h.get("url") == url]

    @staticmethod
    def _id(hook):
        return str(hook["self"]).rstrip("/").rsplit("/", 1)[-1]

    def save(self, existing, payload):
        if existing:
            hook_id = self._id(existing[0])
            status, body = _call("PUT", f"{self.base}/{hook_id}", self.headers, payload)
            _expect("Updating the Jira webhook", status, body)
            return hook_id, "updated"
        status, body = _call("POST", self.base, self.headers, payload)
        return self._id(_expect("Creating the Jira webhook", status, body)), "created"

    def delete(self, hook):
        status, body = _call("DELETE", f"{self.base}/{self._id(hook)}", self.headers)
        _expect("Deleting the Jira webhook", status, body)
        return self._id(hook)


def _signed_check(url, secret):
    """Deliver one request signed the way Jira signs, to prove the pair works."""
    body = json.dumps({"webhookEvent": CHECK_EVENT}).encode()
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Content-Type": "application/json", "X-Hub-Signature": f"sha256={signature}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return "ok" if resp.status == 200 else f"HTTP {resp.status}"
    except urllib.error.HTTPError as exc:
        return f"HTTP {exc.code} {_redact(exc.read().decode('utf-8', errors='replace'))[:200]}"
    except urllib.error.URLError as exc:
        return f"unreachable: {exc.reason}"


def apply(args, openhands, jira):
    global _secret
    jira.require_admin()
    jql = args.jql or 'labels = "{}"'.format(args.label.replace("\\", "\\\\").replace('"', '\\"'))
    name = args.name or f"OpenHands: issues labelled {args.label}"
    webhook = openhands.find()
    # Asked before anything is written: it proves Jira serves this account the
    # webhook API, and says whether Jira already holds this webhook's secret.
    in_jira = jira.find(webhook["webhook_url"] if webhook else None)
    # A pair that exists on both sides keeps its secret, so a failure half way
    # through cannot leave Jira signing with one OpenHands no longer accepts.
    new_secret = args.rotate_secret or not (webhook and in_jira)

    if args.dry_run:
        if not webhook:
            openhands_plan = f"register source '{args.source}'"
        elif new_secret:
            openhands_plan = "rotate the secret of the existing one"
        else:
            openhands_plan = "keep the existing one and its secret"
        return {
            "dry_run": True,
            "openhands_webhook": openhands_plan,
            "jira_webhook": "update the existing one" if in_jira else "create",
            "jira": {"site": jira.site, "name": name, "events": JIRA_EVENTS, "jql": jql,
                     "url": webhook["webhook_url"] if webhook else "(assigned on registration)"},
        }

    payload = {"name": name, "events": JIRA_EVENTS, "excludeBody": False,
               "filters": {"issue-related-events-section": jql}}
    if webhook:
        webhook = openhands.align(webhook)
        if new_secret:
            _secret = openhands.rotate(webhook)
    else:
        _secret = secrets.token_urlsafe(32)
        webhook = openhands.create(_secret)
    url = webhook["webhook_url"]
    if not url.startswith("https://"):
        raise Failure(f"Jira only delivers to HTTPS URLs, and this deployment's is {url}")
    if new_secret:
        # Left out otherwise: Jira keeps the secret of a webhook updated without one.
        payload["secret"] = _secret

    try:
        hook_id, action = jira.save(in_jira, {**payload, "url": url})
    except Failure as exc:
        if not new_secret:
            raise
        raise Failure(f"{exc} OpenHands now holds a signing secret that Jira does not, so "
                      "Jira's deliveries are refused until apply succeeds; run it again once "
                      "the cause is fixed.", exc.code) from exc

    return {
        "openhands_webhook": {"id": webhook["id"], "source": webhook["source"], "url": url},
        "jira_webhook": {"id": hook_id, "action": action, "name": name,
                         "events": JIRA_EVENTS, "jql": jql},
        "signing_secret": "new" if new_secret else "unchanged",
        "signed_delivery_check": _signed_check(url, _secret) if new_secret
                                 else "skipped: the secret was not changed",
    }


def delete(args, openhands, jira):
    jira.require_admin()
    webhook = openhands.find()
    if not webhook:
        return {"deleted_jira_webhooks": [],
                "note": f"No OpenHands webhook with source '{args.source}', so no Jira webhook to match."}
    return {"deleted_jira_webhooks": [jira.delete(h) for h in jira.find(webhook["webhook_url"])],
            "note": "The OpenHands webhook is left in place; it receives nothing now."}


def main():
    parser = argparse.ArgumentParser(description="Set up the Jira Cloud webhook of an event-based automation.")
    parser.add_argument("action", choices=["apply", "delete"])
    parser.add_argument("--jira-base-url", required=True)
    parser.add_argument("--jira-email", required=True)
    parser.add_argument("--openhands-host", required=True)
    parser.add_argument("--jira-token-env", default="JIRA_CLOUD_KEY")
    parser.add_argument("--source", default="jira")
    parser.add_argument("--label", default="create-pr")
    parser.add_argument("--jql")
    parser.add_argument("--name")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--rotate-secret", action="store_true")
    args = parser.parse_args()

    api_key = os.environ.get("OPENHANDS_API_KEY", "")
    token = os.environ.get(args.jira_token_env, "")
    try:
        if not api_key:
            raise Failure("OPENHANDS_API_KEY is not set.", code=2)
        if not token:
            raise Failure(f"{args.jira_token_env} is not set. Store the Jira API token as an "
                          "OpenHands secret and name it in the command.", code=2)
        if urllib.parse.urlparse(args.jira_base_url).scheme != "https":
            raise Failure("--jira-base-url must be an https:// URL.", code=2)
        if urllib.parse.urlparse(args.openhands_host).scheme != "https":
            raise Failure("--openhands-host must be an https:// URL: Jira only delivers "
                          "webhooks over HTTPS.", code=2)
        openhands = OpenHands(args.openhands_host, api_key, args.source)
        jira = Jira(args.jira_base_url, args.jira_email, token)
        result = (apply if args.action == "apply" else delete)(args, openhands, jira)
    except Failure as exc:
        print(_redact(str(exc)), file=sys.stderr)
        sys.exit(exc.code)
    print(_redact(json.dumps(result, indent=2)))


if __name__ == "__main__":
    main()
