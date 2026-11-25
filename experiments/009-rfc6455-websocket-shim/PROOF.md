# 009 — Result

| prediction | result |
|---|---|
| 1. frame round-trip at 0/125/126/65535/65536, fragments, UTF-8 | **held**: 5/5 ERT (`websocket-test.el`) |
| 2. 101 + matching `Sec-WebSocket-Accept` from uvicorn | **held** |
| 3. inbox prints with no client edits | **refuted**: transport fixed, then `Assertion failed: deltas` |
| 4. rejected handshake fails once | **held**: `/nope` → one 403, `closes=0`, no recursion |

The RFC 6455 accept value in the first test draft was typed from memory and
was wrong; the implementation was right. Checked against Python's
`hashlib`/`base64`, not against recollection.

Refutation of (3) moved the problem one layer up: the server answers every
open request with `"2": []`. That is experiment 010.

Run:

    emacs -Q --batch -L lisp -l experiments/009-rfc6455-websocket-shim/websocket-test.el \
      -f ert-run-tests-batch-and-exit
