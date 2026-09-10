# Demo architecture and decision record

## Goal

Tools need not be reimplemented; existing work can be re-entered from another device; transmitted information is explicit and bounded. New project, no dependency on Tabverse. This demo selects an implementation to learn from, not a final universal architecture.

## Execution and identity

The existing application is the only writer/executor. The Host adapter lists real on-screen windows. Selection stores a CG window ID, PID and application launch timestamp, preventing silent attachment to a replacement process. Hidden, closed, moved and ambiguous windows fail explicitly. Viewers can disconnect without terminating host applications. Host restart/OS migration/offline operation are separate capabilities, not implemented.

## Two projections

Semantic: a bounded macOS AX traversal yields roles, labels, values and declared press/set capabilities. Password controls are not included. Each snapshot has an expiring revision and cached native handles; action time revalidates the control state. Snapshots are full, manual reads in this version, not ongoing semantic deltas. Incompleteness is always visible.

Visual: screencapture reads one selected window. ROI cropping and downsampling precede tile comparison. Each 128px tile is hashed in raw RGB; only changed tiles are JPEG-encoded. The wire body is a 4-byte JSON-header length, bounded JSON metadata and concatenated raw JPEGs. No base64. A missing/mismatched baseline, crop or quality change forces a new baseline. No default polling; optional foreground-only 3-second pulls. Static tiles have no JPEG bodies. Animation can still be expensive.

Both projections observe the same application window. Semantic actions invalidate the image scene. Visual input requires the current foreground application/window and unchanged geometry, uses normalized ROI coordinates and refuses stale frames. This is not DOM replication or pixel-free full application replication.

## Transport and trust

Python standard-library HTTP server, maximum eight concurrent handler threads, serialized native adapter, bounded JSON request sizes. Random launch bearer token, per-viewer sessions, Host/Origin validation, no CORS. A single 120-second control lease prevents competing viewers. Action IDs and payload digests preserve at-most-once attempts in each live session; no automatic replay after ambiguous transport failure. No cloud or relay is required for LAN tests. TLS/VPN/private HTTPS termination is external or CLI-supplied cert/key.

## Deliberate non-goals

No new terminal/browser/editor frontends; no application-specific Codex backend; no filesystem sync; no WASM; no continuous video/audio; no automatic UI agent; no browser-network proxy; no migration. These are candidates for later comparison, not prohibited technologies.

## Evaluation next

Measure actual TextEdit, private website and Codex tasks on the user's Mac and phone. Separate AX availability, control success, scene continuity, first-load bytes, incremental bytes, reconnection and actual cellular/VPN overhead. Use the results to decide whether native session protocols, another display codec/transport, improved AX mapping or a persistent workspace host is most valuable. Do not infer carrier savings or universal compatibility from fixture tests.

## Primary API references

- Apple AX model: https://developer.apple.com/library/archive/documentation/Accessibility/Conceptual/AccessibilityMacOSX/OSXAXmodel.html
- PyObjC ApplicationServices: https://pyobjc.readthedocs.io/en/latest/apinotes/ApplicationServices.html
- PyInstaller macOS packaging: https://pyinstaller.org/en/stable/feature-notes.html
- Tailscale Serve: https://tailscale.com/docs/reference/tailscale-cli/serve
- GitHub runner architectures: https://docs.github.com/en/actions/reference/runners/github-hosted-runners
