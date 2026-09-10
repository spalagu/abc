# Security boundary — experimental demo

This is remote control of your logged-in Mac, not a sandbox. Only run code you trust. Possession of the launch token grants access to visible windows and supported input. Do not expose its HTTP listener to the public Internet.

Default binding is loopback. LAN mode requires explicit selection and consent and is **unencrypted HTTP**. Use only a trusted test network, or protect traffic with your own authenticated private HTTPS/VPN. External HTTPS origins are explicit; forwarded headers never implicitly expand trust. No public relay, UPnP, router configuration, telemetry, remote shell endpoint or arbitrary file endpoint is included.

Each start generates a cryptographically random 256-bit bearer token. The token travels in a URL fragment for pairing, is removed from the address bar, and is sent in Authorization headers. The client keeps it in sessionStorage, not localStorage. It expires after 12 hours or server shutdown. Tokens and content are not logged. A copied QR code or pairing URL is a credential. Clear your clipboard when no longer needed.

The server checks Host, Origin, request content type and length. API actions are serialized, limited to a single controller lease, bound to a selected window/process identity, and require recent snapshots. Request IDs deduplicate action attempts within a live client session. Expiry or restart is not cross-process exactly-once execution. The UI never automatically retries actions with unknown results. No promise is made that arbitrary applications expose safe or complete accessibility metadata.

Explicit secure AX controls are hidden, but screen images may still contain secrets. Snapshot state exists in RAM. System screencapture writes a window PNG to an OS-created private temporary directory which is deleted after reading; the host does not retain screenshot history. Python memory and macOS swapping are outside this demo's secure-erasure guarantees.

Frame budgets cover accepted encoded frame response bodies across all authenticated clients. They do not cap all HTTP/TCP/TLS/VPN or unauthenticated traffic; these are not billing guarantees. Sessions, requests, image dimensions, node traversal and text sizes are bounded. This prototype's standard-library HTTP server is not an Internet-facing hardened production gateway.

It does not unlock the screen, operate loginwindow, alter security settings, bypass protected controls, auto-approve agent actions, move credentials between hosts, or kill your work. Keep Host awake for a test; no sleep or login configuration is changed automatically.

Builds use ad-hoc signing, not Developer ID notarization. Verify release checksums and the corresponding workflow before opening. Do not disable Gatekeeper globally. Bundled dependency versions are attached to build artifacts. Native macOS permissions and application-specific compatibility still require manual acceptance.
