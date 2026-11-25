# 016 — Proof: static mock corpus

Built: `resources/corpus/waves.json`, `src/wave_client_server/corpus.py`,
`scripts/load-corpus.py`, `tests/test_corpus.py`, `gmake db-corpus` /
`server-corpus`, avatars for frank, grace, heidi, ivan, judy
(`gen-avatars.py` now also scans `resources/corpus/*.json`).
`synthetic.py`, `wave_server.py` and `user_api.py` are unchanged.

## Corpus

28 waves, 195 blips, 93 per-user state rows, 26 HN stories.

| topic | holders | waves (HN id) |
|---|---|---|
| google-wave (2009-2010) | alice bob charlie dave erin frank | 752340, 883116, 1354427, 1361394, 1575892, + 2 without a story |
| agent-sandboxing | bob dave heidi | 49239751, 47343927, 46436828 |
| formal-methods | charlie grace heidi | 18965274, 49909056, 13440324 |
| repl-lisp | alice frank ivan | 16307882, 23418699, 41600903 |
| unix-history | bob dave frank judy | 45840321, 29521506, 15865504 |
| testing | charlie erin ivan | 45818562, 40875559, 26024915 |
| literate-publishing | alice grace judy | 47300747, 15321850, 12046950 |
| ml | erin grace ivan | 16493489, 28613099, 28521992 |

The six-holder Wave topic is what makes the >= 6 participant wave
("Google Kills Wave", with the all-columns-voted poll) possible without any
user leaving their interests.

## Results

| # | prediction | result |
|---|---|---|
| 1 | validator empty and not vacuous | **held** — `test_corpus_is_valid`, `test_validator_catches_broken_corpora` |
| 2 | all 15 UI features | **held** — `load-corpus.py` prints 15 × `ok`; `test_every_ui_feature_is_covered` |
| 3 | interest exclusivity | **held** — `test_interest_exclusivity` (creators, participants, authors, voters, state rows) |
| 4 | snapshot holds metadata only | **held** — `test_hn_snapshot_holds_only_metadata_and_shape`; the fetch script reduced each item to shape before writing anything |
| 5 | unchanged server serves it per user | **held** — see below; also `test_loaded_corpus_serves_per_user_views` |
| 6 | no PII, no deny-listed words | **held** — `test_no_pii`, `test_no_deny_listed_words` |

`uv run --extra test pytest -q --ignore=tests/broken`:
`4 failed, 98 passed` — the four are the pre-existing
`test_http_api` ×3 and `test_rest_extended::test_root_returns_200`.
`tests/test_corpus.py` alone: `11 passed`.

Server on port 9893 against `corpus.db`, Basic auth:

- `alice:alice` `/api/waves?folder=all` → 12 waves (Wave, REPL, literate),
  e.g. `gw4` 5 unread, `lp3` 3 unread, `gw5` fully read.
- `heidi:heidi` → 7 waves (sandboxing, formal methods) plus `gw4`, which is
  public; `/api/folders` shows the custom `sandbox` folder.

## Deviations and what was not shown

- 2009-2010 waves sit before `synthetic.BASE_TIME` (2026-01-01); the
  conversion uses negative `start_minutes`, which `write_world()` handles.
  Consequence: the `active` folder (7-day window) is empty for everyone.
- A public wave is visible to users who do not hold its topic (heidi sees
  `gw4`). Exclusivity is about acting (creating, joining, replying, voting,
  state rows), not about what a public wave shows; no such user has state on it.
- The shape rule fixes the blip count and caps depth; the branching within
  that is hand-written to echo `largest_threads`, not derived from it.
- The deny-list is short and generic by design; tone was otherwise kept
  civil by writing, not by a classifier.
- `uv` picked Python 3.14 in a fresh worktree and pydantic-core 2.33 does
  not build there; the run used 3.13 (`UV_PYTHON=3.13`).
