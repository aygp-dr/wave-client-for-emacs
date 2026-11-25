# 009 — RFC 6455 shim behind the 2010 websocket API

## Conjecture

The 2010 Wave client's only incompatibility with the local FastAPI server is
the transport: its vendored `websocket.el` speaks hixie-76 (Key1/Key2
handshake, `\0...\377` framing), and uvicorn rejects that handshake with 400.
Replacing `lisp/websocket.el` with an RFC 6455 implementation that keeps the
same four entry points (`websocket-open`, `websocket-send`, `websocket-openp`,
`websocket-close`) is enough for the unmodified client to fetch the inbox.

## Observed before the change

- `gmake elisp-list-waves` → `error in process sentinel: Lisp nesting exceeds
  'max-lisp-eval-depth': 1601`
- server log: repeated `connection rejected (400 Bad Request)`
- cause of the recursion: `wave-client-ws-onclose` reconnects synchronously,
  and the old sentinel fires it on every failed handshake.

## Prediction

1. Frame encode/decode round-trips for payload lengths 0, 125, 126, 65535,
   65536 (each length-encoding branch), and fragmented messages reassemble.
2. A handshake against uvicorn returns 101 with a matching
   `Sec-WebSocket-Accept`.
3. `gmake elisp-list-waves` prints `=== INBOX (5 waves) ===` against the
   seeded DB, with no edits to `wave-client*.el`.
4. A rejected handshake (wrong path) fails once, not recursively.

## Refuted if

- (3) needs changes to the client files: the problem is bigger than transport.
- (4) still recurses: the guard is in the wrong layer.
