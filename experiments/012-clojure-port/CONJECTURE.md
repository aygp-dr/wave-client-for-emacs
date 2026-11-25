# 012 — Port the server to Clojure (spoke: wave-client-for-emacs-clj)

## Conjecture

The Python server is small enough, and its wire behaviour narrow enough, that
a direct Clojure translation (http-kit + next.jdbc/sqlite, a pure `fedone`
namespace) reaches byte parity with it on every route against the same seeded
database, and the unmodified 2010 Emacs client cannot tell the two apart.

The Python server is the oracle: expected values come from running it, not
from reading it. Parity is measured route by route by capturing the Python
response and the Clojure response for the same request against copies of one
seeded DB and diffing them.

## Predictions (written before the build)

1. **WS open, byte parity.** `ProtocolOpenRequest` for `indexwave!indexwave`,
   `localhost!w+abc123`, `localhost!w+ghi789` and an unknown wave produce the
   same text frames, byte for byte, including Python's `json.dumps` separators
   (`", "`, `": "`) and `ensure_ascii` escaping, provided the Clojure side
   writes JSON the way Python does rather than the way `data.json` does.
2. **REST, byte parity.** `/`, `/api/inbox`, `/api/waves/{id}` (found and
   404), unknown path (404) and wrong method (405) return the same status,
   content type and body. `/health` matches in shape; its timestamp differs.
3. **Timestamps diverge by the UTC offset.** `creation_time` /
   `last_modified_time` in `/api/waves/{id}` differ by exactly the host's UTC
   offset, because Python calls `.timestamp()` on naive datetimes that hold
   UTC (seeded by SQLite `datetime('now')`, written by `utcnow()`), which
   treats them as local time. With the oracle run under `TZ=UTC` they match.
4. **Submit.** add/remove participant and camelCase/snake_case input match.
   `documentOp` and a submit that creates a new wavelet return 500 from
   Python (`op.doc_op` is not an attribute; `version` is `None` before
   insert). The port fixes both; these are declared divergences, not parity
   failures.
5. **OpenAPI.** `/openapi.json` has the same `paths`, methods and
   `operationId`s (`root`, `health_check`, `get_inbox`, `get_wave`,
   `submit_delta`), so `restish api connect` produces the same commands
   (`get-inbox`, …) against 9899.
6. **Client acceptance.** `scripts/wave-ws-inbox.el` pointed at
   `ws://localhost:9899/ws` prints `=== INBOX (3 waves) ===`, with the same
   three waves, digests and creators as against 9898, with no client change:
   http-kit's RFC 6455 handshake is accepted by the 009 shim.
7. **Properties.** For arbitrary snapshot content (strings, empty strings,
   elements with and without attributes, leading line or not), synthesized
   updates have consecutive delta versions from 0, a final version equal to
   the op count, at least one delta per update, and balanced element
   start/end in every document; 1000 trials each pass.

## Refuted if

- any WS frame differs after JSON serialization matches Python's (that would
  mean the port's logic differs, not its printer);
- the 2010 client needs any change, or a different script, to read the inbox
  from 9899 (beyond the URL);
- the timestamp divergence is not exactly the UTC offset (then the bug is
  something other than naive-local interpretation);
- a property finds a counterexample in the *Python* behaviour too (then the
  spec, not the port, is wrong).
