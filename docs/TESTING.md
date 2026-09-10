# Evidence and scope

## Local checks performed while authoring

- Python compile check and `node --check web/app.js`.
- 24 standard-library unit/integration tests: binary frame layout, unchanged frames, single-tile differences, baseline recovery, crop/parameters, invalid ROI/numeric inputs, budget atomicity, controller lease, revocation, deduplication, stale scene/changed native state, reconnect with preserved fixture state, process replacement, shared budgets, HTTP authentication, cross-origin requests, Host rebinding, malformed/oversized JSON, static content isolation and response security headers.
- Native macOS adapter **not run** in the Linux authoring environment.
- A Chromium mobile-viewport test was written and attempted locally, but this environment rejects localhost browser navigation with `ERR_BLOCKED_BY_ADMINISTRATOR`. No local browser-interaction pass is claimed. The test is included in GitHub Actions; its actual run result is the authority.

## CI requirements before a release exists

Linux repeats protocol/security tests and the real Chromium client over local HTTP with the explicitly synthetic adapter. macOS jobs test protocol code, load native framework symbols, bundle the application for Apple Silicon and Intel, verify ad-hoc signatures and launch the bundled import/assets smoke check. Both architectures and Linux must pass before the release job runs.

The browser fixture has a conspicuous TEST FIXTURE label. It is never selected automatically, and does not prove Codex/macOS AX compatibility. Neither import checks nor package signing validate screen-recording consent, accessibility consent, native input, Tailscale, Safari/iPhone behavior or locked/sleeping Mac behavior.

Manual acceptance of the real host is required. See ACCEPTANCE.zh-CN.md. Record exact app/OS versions locally, task result and an exported content-free diagnostic. Do not upload tokens, private text or screenshots to this public repository.
