# 017: Wave in a Box 0.3 as a protocol oracle

## Conjecture

A surviving Wave in a Box image can serve as a compliance oracle: our server
and the 2010 Emacs client speak the same client-server protocol it does, so
captured frames become golden tests.

## Result: the oracle runs, and the conjecture is half refuted

Our server, and the client it was built for, follow **FedOne as of 2010**.
Wave in a Box 0.3 (2014) shares the protobuf field numbers but differs on
the wire in four ways, so neither the Emacs client nor our server
interoperates with it as-is. The field numbers are the shared contract;
the envelope, transport and update shape are not.

## Setup (2026-11-26)

- Image `docker.io/maccam912/docker-apache-wave:latest`: built 2014-11-12,
  amd64, 3.1 GB, Wave in a Box `waveinabox.version=0.3`, Java 1.6.0_32,
  Jetty 7.1.6 (July 2010), domain `local.net`, in-memory stores.
- Current Docker refuses it (schema-1 manifest support removed); Podman
  still pulls and converts it. Runs under amd64 emulation on arm64.
- `podman run -d --name wiab-oracle --platform linux/amd64 -p 127.0.0.1:9897:9898 docker.io/maccam912/docker-apache-wave:latest`
  (localhost only, port 9897 so it doesn't collide with our 9898/9899).
- Users: `POST /auth/register` (address, password), then
  `POST /auth/signin` (address@local.net, password) for a `JSESSIONID`.
- Websocket at `/socket` (also `/socket.io/*`; `use_socketio = true`).
- `capture_hixie76.py` records every frame both ways as JSONL; scripted
  steps are in `frames/steps-*.json`, captures in `frames/*.jsonl`.

## Differences found (each with the frame that shows it)

| # | Wave in a Box 0.3 | FedOne 2010 / our server + Emacs client | evidence |
|---|---|---|---|
| 1 | websocket **hixie-76** only (Jetty 7.1.6); an RFC 6455 upgrade falls through to GET and gets 405 | the original client spoke hixie-76 too (`lisp/legacy/websocket-hixie76.el`); we moved client and server to RFC 6455 | `open.jsonl` handshake line |
| 2 | envelope `{messageType, sequenceNumber, message: {...}}`, message as an **object** | client sends `{version, sequenceNumber, messageType, messageJson: "<string>"}` | `WebSocketChannel.MessageWrapper` in the image; `lisp/wave-client-websocket.el` `wave-client-ws-send` |
| 3 | on open, existing state arrives as a **snapshot** (field 5) with an **empty** delta list; a marker update (`"6": true`) ends the initial state | client replays deltas only and asserts each update has at least one; `fedone.py` synthesizes deltas from snapshots for it | `reopen.jsonl` |
| 4 | the submitter's channel gets a commit notice (`"3"`), not its own delta echoed | (to check against our server) | `create.jsonl` |

Encoding details the golden tests must pin:

- Wave ids and wavelet names are slash-separated with `~` for "same domain":
  `local.net/w+oracle4/~/conv+root`.
- The version-zero history hash is the UTF-8 of the wavelet URI **without**
  the `~`: `wave://local.net/w+oracle4/conv+root`. Using the `~` form is
  rejected: `Mismatched hash at version 0`.
- Hashes are **uppercase** hex; lowercase is rejected
  (`Not a hexadecimal digit: a`). Later hashes are 20 bytes.
- Channel ids are server-wide (`ch1`, `ch2`, ...), not per connection; a
  submit must carry the id the open announced (field 7).
- int64 versions in hashed versions come back as floats (`2.0`); int64
  fields in snapshots come back as two-element arrays (`[2, 0]`,
  `[424001525, 418]`).

## What this means

- For the hosted (babashka) server: decide which dialect it speaks.
  FedOne-2010 keeps the Emacs client working unchanged; Wave in a Box 0.3
  is the only dialect with a surviving reference implementation. A server
  can speak both, chosen by envelope (`messageJson` string vs `message`
  object), since nothing else on the wire conflicts.
- The golden tests should pin the encoding rules above whichever dialect
  wins, since both share them.

## Next

- Capture a second participant (bob) receiving alice's delta live: does a
  non-submitting channel get the delta itself, or a snapshot?
- Build the console client inside the image (`ant` target for
  `waveinabox-client-console`; only the server jar is in `dist/`) for a
  second reference client.
