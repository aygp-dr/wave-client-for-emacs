# 010 — Synthesize FedOne deltas from stored snapshots

## Conjecture

The client never reads document snapshots; it rebuilds every wavelet by
replaying `ProtocolWaveletDelta`s and asserts each update has at least one.
If the server synthesizes, from the snapshot docs it already stores:

- for `indexwave!indexwave`: one wavelet per wave, named
  `wave://localhost/indexwave!indexwave/<wave-local-id>`, with add-participant
  ops and a `digest` doc;
- for a wave: one `conv+root` wavelet with a `conversation` manifest and one
  `b+…` blip doc per stored wavelet (replies folded in);

with delta versions chained from 0, then the 2010 client's own
`wave-ws-get-inbox` and `wave-ws-get-wave` produce the inbox and a renderable
conversation.

## Refuted if

- the client needs changes beyond `wave-client-ws-translate-inbox` (whose
  digest and creator are marked `TODO(ohler)` in the 2010 source);
- version chaining is wrong: `wave-apply-delta` silently skips deltas whose
  pre-version does not match, so the symptom would be missing blips, not an error.
