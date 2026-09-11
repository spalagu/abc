# Evidence and scope

## 0.1.1 local authoring checks

38 cross-platform tests pass; the macOS-only native test is skipped on Linux. Python compile check and JavaScript syntax check pass. Local Chromium navigation is blocked with ERR_BLOCKED_BY_ADMINISTRATOR by the authoring environment, so browser acceptance runs in GitHub Actions rather than claiming a local pass.

The original 24 tests cover binary frames, static/single-tile updates, resync, ROI/numeric input, budget atomicity, controller/revocation, deduplication, stale snapshots, reconnect to preserved fixture state, process replacement and HTTP security.

Fourteen new fake-framework tests cover left/right differentiation, AXShowMenu, ancestry containment, secure controls, no silent fallback, no global/activation calls in background paths, selected AXFocusedWindow matching, Unicode, geometry revalidation, uncertain delivery and observed foreground changes. Mock tests do not prove native event execution.

## CI release gates

Chromium and WebKit execute real mouse/touch events through the browser client and HTTP to the explicitly labelled fixture. Checks include right-menu suppression only when input is enabled, one request per click, right-button tap on mobile and adjacent/visible server refusal. The existing browser smoke test covers semantic write, reload continuity, image delta and private-content-free diagnostics.

The macOS-only test constructs native mouse/key events and checks public symbols/fields and AX identity equality. It never posts events or changes TCC permissions. Mac jobs also construct the actual Cocoa host window, package both architectures, verify ad-hoc signatures and run bundled import/assets smoke checks. All jobs must pass before release publication. CI run results, not this test inventory, determine pass/fail.

## Not established by automation

Actual background input into Lens/Codex, real macOS permission acceptance, iPhone/Safari behavior, private-network/VPN connectivity, execution acknowledgement and independent popup menu capture. WebKit tests are not a physical iPhone test. No automated test claims universal background control.

Use ACCEPTANCE.zh-CN.md and content-free diagnostics for real testing. Do not upload tokens, window content or sensitive screenshots to this public repository.
