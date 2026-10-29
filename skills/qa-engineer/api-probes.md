# API probes

Send these through the web origin from the signed-in browser, so cookies and the proxy are the real ones, never the API's own port:

```bash
agent-browser --session qa-a eval 'fetch("/api/<route>", {headers: {"X-Requested-With": "<value>"}}).then(async r => ({status: r.status, type: r.headers.get("content-type"), body: await r.text()}))'
```

Outside a browser (a `curl` for a handoff's Acceptance), still go through the origin with the cookie jar from `qa_login.py --jar <file>` (`curl -b <file>`), and send the adapter's required header on every non-GET: a 4xx without it is the guard working, not a finding, so resend with the header before judging:

```bash
curl -sS -b <evidence>/<role>.jar -H '<required header>' "<origin>/api/<route>"
```

The oracle is the adapter's API spec. A live response that disagrees with the spec is a finding; so is a spec that disagrees with the code, though that usually means someone skipped regenerating it and the project's build or generation gate would have caught it: drift that gate already catches is not a QA finding.

- **Error shape.** Walk every documented endpoint and provoke every failure it can give: signed out, wrong tenant, malformed body, missing field, unknown id, a business-rule refusal. Each answers the project's one error shape (often `application/problem+json` with a non-null `detail` and a stable error key), including errors the framework raises before any handler runs: unknown routes (404) and unparseable bodies (400). A null `detail`, a missing key or an unreadable message there is a real finding. Ask again with each supported `Accept-Language`: the sentence changes, the key doesn't. A key with a sentence in one language only is a finding the project's message-catalog test should have caught, which makes it doubly worth reporting.
- **Tenant isolation.** Sign two roles of different tenants into two sessions. As B, list, read and change A's rows by id (the adapter's tenant-owned resources, e.g. products, verification, audit entries). Each must answer not found or forbidden, never A's data and never a server error. Change only rows the run created; never modify another tenant's existing data to prove the point. The filter usually reads the caller through the data context, so this journey proves the claim end to end rather than in a test fixture. Not a leak: data owned by the platform and shared by design (a category tree and its fields), and reads on the project's cross-tenant allow-list, each with its reason; a seller's own side of a cross-company record is the same kind of read. Read the module's notes before calling either a finding.
- **Paging under writes.** Page through the adapter's paged lists with the documented cursor; fetch page one, insert a row that sorts into page one, fetch page two, and check nothing was skipped or repeated (the point of keyset over offset). Then a cursor from another endpoint, a hand-mangled cursor and another tenant's cursor: each a clean 400 with an error key, never a 500 and never another tenant's page.
- **Anonymous surface.** With no session, enumerate every endpoint that answers and compare against the set the code declares anonymous. An endpoint open that the policy doesn't name is the highest-severity finding here, a blocker; the other direction counts too: sign-in endpoints that refuse anonymous callers make the product unusable. Dev-only routes are anonymous on purpose and exist only beside a mocked provider; they must not exist where the provider is real.
- **Rate limits and forwarded headers.** Confirm through the origin that the limiter engages, and that its partition (often the client IP) can't be picked by a header you set yourself (`X-Forwarded-For` and similar). Locally nothing sits in front of the web proxy, so a header you send is the hop the API trusts when only that proxy reaches it: expected here and proof of nothing about staging, where the adapter's deployment check is the test. Anything else that lets you pick the partition end to end is a blocker.
- **Six different answers.** No data, not found, forbidden, unauthenticated, malformed input and server failure look alike from a `curl` and need six different fixes. A 404 that should be a 403 is a finding; a 500 that should be any of the others always is.
- **Sanitize.** Every captured request and response is stripped of cookies, `Authorization` headers, passwords and real company data before it is saved.
