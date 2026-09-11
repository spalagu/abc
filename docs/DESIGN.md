# Demo architecture

Tools need not be reimplemented; the existing app remains the writer/executor. Viewers re-enter the same work, not a synchronized second copy. Independent of Tabverse; this demo is a testable implementation, not a frozen universal architecture.

Selection stores CG window ID, PID and launch timestamp. Closed, hidden or replaced windows are rejected rather than silently followed. Disconnecting a viewer does not terminate Host work. Host restart, offline execution and migration are separate, unimplemented capabilities.

Semantic projection is a bounded AX traversal. It reports partial coverage and excludes explicitly secure controls. Snapshot revisions and native handles are checked at action time. This version uses manual full semantic reads, not automatic semantic deltas.

Visual projection captures one window, crops ROI and downsamples before hashing 128px raw RGB tiles. Changed tiles become JPEGs. The binary response is a four-byte JSON header length, metadata and concatenated JPEGs. No base64. Baseline loss or parameter changes force a full baseline. Default manual pulls; optional three-second pulls stop when the page hides. The host-wide frame budget is separate from other traffic and protocol overhead.

## Input in 0.1.1

Default background AX maps a screenshot position to a control scoped to the target application, verifies ancestor containment in the selected window, then uses AXPress or AXShowMenu if declared. No global hit-test result is trusted without ancestry validation. Failed/unsupported actions do not automatically retry through another mechanism.

Explicit experimental PID input verifies AXFocusedWindow and, for keyboard/text, focused-element ancestry and non-secure status. CGEventPostToPid and public window hints are not guaranteed window-specific execution; the response is submitted_unconfirmed. Background paths never call activation, AXRaise or global CGEventPost. A separate legacy foreground mode checks the current foreground window and still never activates automatically. All routes retain geometry and scene-age checks.

Browser contextmenu is intercepted only over an input-enabled canvas. Left/right identity and the pointer-down scene revision are transmitted. Busy clicks are visibly rejected, not queued. Action errors appear beside the image and in a floating notification, not only at page top.

## Transport and boundaries

Bounded standard-library HTTP server, serialized native operations, per-launch bearer credential, explicit Host/Origin checks, one controller lease and per-session request-ID deduplication. No retry after uncertain side effects. Private TLS/VPN remains external or uses CLI-supplied certificate/key. No arbitrary shell or file endpoint.

No special terminal/browser/editor UI, Codex private backend, filesystem sync, WASM, continuous AV, UI agent or migration. These remain future candidates. Independent popup windows may not appear in a single-window capture. Actual app compatibility must be measured; fixture tests are not compatibility evidence.

See INPUT-FIX.md, TESTING.md, SECURITY.md and ACCEPTANCE.zh-CN.md.
