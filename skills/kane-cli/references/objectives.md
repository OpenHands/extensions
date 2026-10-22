# Writing Kane CLI objectives

The objective string decides what the agent does. Four patterns cover most checks.

| Pattern | Words that trigger it | What happens |
|---------|-----------------------|--------------|
| Action | "go to", "click", "type", "search", "fill" | Performs browser actions |
| Assertion | "verify", "assert", "confirm", "check that" | Passes or fails on a condition |
| Extraction | "store X as 'name'" | Saves a value into `run_end.final_state` |
| API call | "call GET/POST <url>", or a pasted `curl` | Makes the HTTP request, then you can assert on the response |

## Rules that make a check reliable

1. End every flow with an assertion about the resulting page, for example "then verify the order confirmation shows a number". A run with only actions has nothing to pass or fail on.
2. Describe actions as goals ("log in with {{username}}") and keep exact data literal or in variables.
3. Use "store ... as 'name'" to capture a value. Words like "read" or "tell me" do not reliably capture it.
4. Refer to a stored value in plain words ("the stored order_id value"). `{{name}}` is only for variables you pass in.
5. Always include the start URL.
6. Split flows longer than about 15 steps into separate runs.

## Examples

```text
Go to https://shop.example.com, search for "laptop", open the first result, then verify the product title contains "laptop"

Go to https://app.example.com/login, log in with {{username}} and {{password}}, then verify the dashboard shows "Welcome"

Go to https://example.com, store the page title as 'page_title', then verify the stored page_title value is not empty

Call GET https://api.example.com/health, save the response as health, then verify the response status is 200
```

Pass variables with `--variables`, and mark secrets so they are masked:

```bash
kane-cli run "Go to https://app.example.com/login, log in with {{username}} and {{password}}, then verify the dashboard shows 'Welcome'" \
  --agent --headless \
  --variables "{\"username\":{\"value\":\"$APP_USER\"},\"password\":{\"value\":\"$APP_PASSWORD\",\"secret\":true}}"
```
