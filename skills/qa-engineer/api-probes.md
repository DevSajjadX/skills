# API probes

Send these through the web origin from the signed-in browser, so cookies and the proxy are the real ones:

```bash
agent-browser --session qa-a eval 'fetch("/api/<route>", {headers: {"X-Requested-With": "<value>"}}).then(async r => ({status: r.status, type: r.headers.get("content-type"), body: await r.text()}))'
```

Check each response against the adapter's API spec. A live response that disagrees with the spec is a finding; so is a spec that disagrees with the code, unless a build or generation gate already enforces regeneration: drift that gate catches is not a QA finding.

- **Required headers.** A 4xx caused by a header the adapter lists as required and the probe left out is the guard working, not a finding; resend with the header before judging.
- **Error shape.** Provoke every failure an endpoint can give: signed out, wrong tenant, malformed body, missing field, unknown id, a business-rule refusal. Each answers the project's one error shape (often `application/problem+json` with a stable error key and a readable message), including errors the framework raises before the handler: unknown routes and unparseable bodies. Ask again in each supported language: the message changes, the key doesn't.
- **Tenant isolation.** Sign two roles of different tenants into two sessions. As B, read and change A's rows by id. Each must answer not found or forbidden, never A's data and never a server error. Read the project's notes on data shared across tenants on purpose before calling a cross-tenant read a leak. Change only rows the run created; never modify another tenant's existing data to prove the point.
- **Paging under writes.** Page through a list with its cursor; insert a row that sorts into page one, fetch page two, and check nothing was skipped or repeated. Then a cursor from another endpoint, a mangled cursor and another tenant's cursor: each a clean client error.
- **Anonymous surface.** With no session, list every endpoint that answers, and compare against what the code declares anonymous. An endpoint open that shouldn't be is a blocker; sign-in endpoints that refuse anonymous callers make the product unusable. Dev or mock routes answering anonymously are expected only beside a mocked provider and must not exist where the provider is real.
- **Rate limits.** Confirm the limiter engages through the origin, and that a header you set yourself (`X-Forwarded-For` and similar) can't pick its partition beyond what the deployment notes say is expected locally.
- **Six different answers.** No data, not found, forbidden, unauthenticated, malformed input and server failure look alike in a response and need six different fixes. A 404 that should be a 403 is a finding; a 500 that should be any of the others always is.
