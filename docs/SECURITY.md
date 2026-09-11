# Security boundary — experimental demo

This is remote control of your logged-in Mac, not a sandbox. Possession of the launch token grants access to visible windows and supported input. Only run code you trust. Do not expose its HTTP listener to the public Internet.

Default binding is loopback. Explicitly consented LAN mode is unencrypted HTTP, for a trusted test network only. Use your own private HTTPS/VPN for untrusted networks. Public origin trust is explicit; forwarded headers do not expand it. No public relay, router configuration, telemetry, remote shell or arbitrary file endpoint.

Each start generates a random 256-bit bearer token. Pairing uses a URL fragment, removes it from the address bar and stores it only in sessionStorage. Authorization headers carry it to the host. Tokens expire after 12 hours or shutdown and are not logged. Pairing QR codes and URLs are credentials. Clear your clipboard when no longer needed.

The server checks Host, Origin, content type and bounded request length. Native actions serialize, require one controller lease, bind to window/PID/launch identity, and require recent scenes. Request IDs deduplicate attempts inside a live session, not across server restarts or expired sessions. No automatic retries after unknown results.

## Input routes

Background AX is default. Hit-testing is scoped to the target app and must return a descendant of the selected window. Secure controls, missing ancestry and unsupported actions are rejected. Failed or attempted AX operations are not silently retried with raw events.

Experimental PID input is explicitly selected by the user. It validates AXFocusedWindow, and focused-element ancestry for text/keys, before using CGEventPostToPid. Public mouse window fields are hints, not an execution guarantee. Apps may ignore input or change their own focus. The client labels the result submitted_unconfirmed. Background routes never call activation, AXRaise or global CGEventPost. The separate foreground route retains foreground checks and never automatically activates.

Canvas contextmenu is suppressed only when input is enabled; read-only and other-page menus remain normal. Busy clicks are visibly rejected, not queued for a later scene.

## Remaining boundaries

Screen images can contain secrets even though explicit secure AX controls are hidden. Screenshots briefly use a private OS temporary directory and are deleted after reading. No history is stored. Secure erasure of Python memory or OS swap is not promised.

The host-wide budget caps accepted encoded frame response bodies, not all HTTP/TCP/TLS/VPN or unauthenticated traffic. This is not a billing guarantee. Sessions, threads, text, node traversal, images and bodies are bounded. The standard-library server is not a hardened public gateway.

No unlocking, security bypass, loginwindow control, automatic approvals, credential migration, forced keep-awake or termination of your work. Ad-hoc signing is not Developer ID notarization; verify checksums and build provenance. Never disable Gatekeeper globally. Actual permissions and app compatibility need real acceptance tests.
