# 012 — Status: paused after the fedone layer (partial result)

Paused on request (focus moved back to the Emacs client and the Python
backend). Nothing below claims more than was run.

## What exists

Spoke `wave-client-for-emacs-clj` (sibling checkout under `aygp-dr/`; local
only — the GitHub repo could not be created from this session, see
"Left undone"):

- standard v1 adopted (`bb check` green, `clj-project-check.sh` prints `ok`);
- `wave-client-server.pyjson`: order-preserving JSON reader, Python's two
  printers (`json.dumps` defaults for WS frames and JSON columns; FastAPI's
  compact form for REST), and `str()` for the inbox digest;
- `wave-client-server.fedone`: direct port of `fedone.py`;
- `fedone_test.clj`: the five examples of `tests/test_fedone.py` plus three
  `defspec`s (1000 / 1000 / 500 trials).

No HTTP server yet: `wave_server.py` has not been ported.

## Oracle

The shared server on 9898 was live and being written to by other sessions
(its index wavelet was at version 16), so expected values came from a
private Python instance on 9897, started from a scratch directory holding a
freshly seeded copy of the DB (`scripts/seed.sql`), and stopped afterwards.
Every probe (REST, 404/405/422, CORS, submits, WS open requests) was
captured from it.

## Parity table

| route | status | evidence |
|---|---|---|
| WS open `indexwave!indexwave` | **byte-identical** (fedone layer) | 3 frames, same bytes as Python |
| WS open `localhost!w+abc123` | **byte-identical** (fedone layer) | 1 frame |
| WS open `localhost!w+ghi789` | **byte-identical** (fedone layer) | 1 frame (image attributes included) |
| WS open unknown wave | **identical** (no frames) | |
| `/`, `/health` | not started | |
| `/api/inbox` | not started | |
| `/api/waves/{id}` | not started | |
| `POST /api/waves/{id}/submit` | not started | |
| `/openapi.json` | not started | |

"fedone layer" means: rows read from the seeded DB, run through
`updates-for-open-request`, printed with `pyjson/dumps`, compared with the
frames the Python server sent. The transport (http-kit RFC 6455) is not
exercised yet.

## Predictions

1. WS byte parity — **held** for the fedone layer once JSON is printed the
   Python way. Not yet tested over a live socket.
2. REST byte parity — untested.
3. Timestamp skew — **confirmed on the oracle side**: `creation_time` for
   a row stored as `2026-11-20 07:27:23` (UTC, from SQLite `datetime('now')`)
   came back as `1795177643`; UTC epoch is `1795159643`. The difference is
   18000 s, the host's offset (EST). Python's `.timestamp()` treats the naive
   UTC value as local time. Planned decision: the port reads it as UTC and
   declares the divergence.
4. Submit — **both crashes confirmed on the oracle**:
   - any `documentOp` → 500, `AttributeError: 'Operation' object has no
     attribute 'doc_op'` (the field is `docOp`; `doc_op` is its alias);
   - a submit that creates a wavelet → 500, `TypeError: unsupported operand
     type(s) for +=: 'NoneType' and 'int'` (column default applies at insert,
     after `version += 1`).
   Even with the attribute fixed, the in-place mutation of the `docs` JSON
   column is not tracked by SQLAlchemy, so the doc would not persist.
   Planned decision: fix all three in the port, declare them.
5. OpenAPI — untested. Note for the port: Python's spec and responses use
   the snake_case aliases (`wavelet_name`, `creation_time`, `doc_id`), not
   the camelCase field names; input accepts both.
6. Emacs client against 9899 — untested (no server).
7. Properties — **held**: balanced blips (1000), chained versions from 0
   for arbitrary wavelet sets incl. empty/`nil` creators and participants
   (1000), JSON round-trip (500). No counterexample.

## Found on the way

- The REST inbox digest is `" ".join(str(item) ...)`, so a `main` doc with
  an element renders Python repr (`{'type': 'line'}`) into the API. The
  seed avoids it because every root wave has a `digest` doc. The port
  reproduces `str()` for parity; arguably a bug.
- Python's dict order is part of the wire format; Clojure maps past 8 keys
  reorder, so the reader builds array maps of any size.

## Left undone / next

1. Port `wave_server.py` (http-kit, next.jdbc): then per route capture →
   diff → fix → commit, filling the table above. Capture script and
   golden outputs were kept only in scratch; rerun them from a fresh seed.
2. Acceptance: `scripts/wave-ws-inbox.el` against `ws://localhost:9899/ws`;
   `restish` against a scratch config.
3. Admin view (`/admin`, Basic auth, cljs) — not started, by request.
4. Create the private GitHub repo `aygp-dr/wave-client-for-emacs-clj` and
   push; creation failed from this session (the active gh account cannot
   create repos under that owner).
