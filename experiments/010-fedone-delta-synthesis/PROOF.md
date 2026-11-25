# 010 — Result: held

`gmake elisp-list-waves` (now `scripts/wave-ws-inbox.el`) against the seeded DB:

    === INBOX (3 waves) ===
      localhost!w+abc123     alice@localhost Discussion: Wave protocol features
      localhost!w+def456     bob@localhost   Emacs client testing
      localhost!w+ghi789     alice@localhost Architecture discussion with diagram

and `wave-ws-get-wave "localhost!w+abc123"` rebuilds:

    conversation by ("alice@localhost"): ((conversation nil) (blip (id "b+root")) end (blip (id "b+reply1")) end end)
    b+root by ("alice@localhost"): ((body nil) (line nil) end "Welcome to ..." ...)
    b+reply1 by ("charlie@localhost"): ((body nil) (line nil) end "Charlie: ..." end)

REST lists 5 entries because it returns raw wavelets (index wave and the
reply wavelet included); the websocket view shows 3 waves, which is the
Wave model.

## Client deviation (declared)

`wave-client-ws-translate-inbox`: digest is the doc's character content
instead of `(format "%S" content)`; creator is the wavelet creator instead of
the literal `"author"`. Both were `TODO(ohler)` / "we don't know" in 2010.

## Found on the way

`wave-ws-get-wave` waits 1s *before* registering its callback, so updates that
arrive within that second never reach it; the data is only in the return
value. The old `elisp-list-waves` target waited on the callback and so always
timed out. The new script uses return values.

## Tests

`tests/test_fedone.py`: 5 pass. Suite outside `tests/broken/`: 37 pass,
4 fail; the same 4 (REST integration) fail at the parent commit.
