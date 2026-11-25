# 014 — Result: held, with seven UI bugs found by the acceptance suite

## Predictions

| # | prediction | result |
|---|---|---|
| 1 | API added without breaking 009/010 | **held**: `gmake elisp-list-waves` lists the seeded inbox; FedOne output for existing seed data unchanged (the Clojure port's byte parity still holds) |
| 2 | REST read state round-trips into the Emacs list | **held**: `wave-ui-shows-unread-badge` sees the badge, opens the wave, sees it gone |
| 3 | A reply from Emacs appears nested via the websocket | **held**: reply typed in Emacs lands under the blip at point; a REST reply from another user is pushed to an open channel (real client, `/socket`) |
| 4 | restish discovers the new operations | **held**: 30 operations; needs `'prompt.credentials.HTTPBasic.username: …'` at connect since routes declare Basic auth |

Refutation criteria not met: no element needed the websocket protocol changed,
and the list is one request per refresh (plus `/api/folders`).

## How the UI is driven by data

`wave_client_server/synthetic.py` defines valid worlds as Hypothesis
strategies and lists `UI_FEATURES` (15 client states). `gen-synthetic-waves.py`
uses `hypothesis.find` with "covers every feature" as the predicate, then asks
the real API for a witness (user, folder, wave) per feature.
`tests/wave-ui-acceptance.el` logs in as each witness and checks the rendered
row and conversation. `gmake elisp-ui-acceptance SEED=n`: seeds 1, 2, 3 each
16/16.

Same seed → same data **for a given strategy version**; editing a strategy
changes what a seed produces.

## What the acceptance suite caught (all fixed)

1. `[muted]` / `[public]` / `#tag` after the title: truncated away by long titles. Now before it.
2. `+N` participant overflow truncated by the name column. Now reserved.
3. Feature "thread depth ≥ 3" counted the root; root replies render beside the root, so it only guaranteed one indent. Redefined as "reply nested 2 deep" (chain of 4).
4. Gadget table flattened into one line: the 2010 renderer fills the paragraph when the body closes. Renderer extension now starts a new paragraph after the element.
5. Test-order dependence: opening a wave marks it read, so a test that opened a witness changed another test's expectation. Acceptance renders with `wave-display`; mark-read is checked explicitly and restored.
6. `M-x wave` inherited the 2010 default backend (browser-channel), which tries google.com ClientLogin. It now forces websocket.
7. auth-source lookup tried to decrypt a real `~/.authinfo.gpg` and blocked on the passphrase. Now opt-in (`wave-ui-use-auth-source`).

Also: `ui-acceptance.sh` killed `uv`'s pid but uvicorn (its child) survived and
held the port; cleanup now kills the listener on the port it used.

## Mutation testing (mutmut, user_api.py + fedone.py)

| run | killed | timeout | survived | score |
|---|---|---|---|---|
| example tests + first properties | 636 | 5 | 374 | 63% |
| + oracle model, round-trip, shape properties | 756 | 50 | 209 | 79% |

The oracle (an independent model of folders, search and summaries computed
from the world spec) took `in_folder` 20→4 and `matches` 59→25 survivors;
the client-replay round trip took `snapshot_to_components` 50→6. Remaining
survivors cluster in auth realm strings, `conversation_update` thread-id
details, and `gadgets_of` defaults: next round.

## Known gaps

- Websocket `ProtocolSubmitRequest` is still dropped (013 divergence 17); Emacs replies go over REST, so `i` in the 2010 `wave-edit` path does nothing.
- Users exist only through wave data; someone in no wave cannot log in, so a public wave is unreachable for them.
- `active` (7-day window) is untested by the oracle: generated worlds are older than the window.
- `/admin` and the logged-in web view are not built yet.
