# 016 — A static, hand-shaped mock corpus

`gen-synthetic-waves.py` (Hypothesis) gives worlds that cover every UI
state but read as word salad. Demos and screenshots want believable
conversations between a stable cast. This experiment checks one in.

## Conjecture

A single hand-written JSON file (`resources/corpus/waves.json`) of ten mock
users with fixed, exclusive interests can, with no generation at load time:

- satisfy every validity rule in `synthetic.py` (parent earlier in the same
  wave, authors and voters are participants, one column per voter, state only
  for users who can see the wave, times increase);
- keep every user inside their own topics, while topics still overlap enough
  for one wave with six or more participants;
- cover every entry of `synthetic.UI_FEATURES`;
- load through the existing `write_world()` by converting to a
  `synthetic.World`, so no second writer is needed;
- use Hacker News for titles, dates, points and comment-tree shape only, with
  every reply original and attributed to the mock users, and still read like
  a thread on that story.

## Design

- Topics: eight, from the owner's research notes (agent sandboxing, formal
  methods, REPL-driven Lisp, Unix history, property/mutation testing,
  org/literate publishing, ML) plus a Google Wave 2009-2010 topic.
- HN stories: picked per topic from the Algolia search API; `/items/ID`
  reduced to `{id, title, created_at, points, comments, top_level_threads,
  max_depth, largest_threads}` before anything was written. Snapshot lives in
  the corpus (`hn_snapshot`), so the loader is offline.
- Shape rule: blips per HN wave = clamp(4, 15, 2 + round(sqrt(comments)/2));
  reply depth <= the story's max depth.
- State: `read_through` names the last blip a user has read; default is the
  user's own last blip, so later replies by others show as unread.
- Loader: `corpus.problems()` (validator), `corpus.to_world()`,
  `corpus.write()` = `write_world()` plus `docs.topic` / `docs.source` on the
  root wavelet. `scripts/load-corpus.py`, `gmake db-corpus server-corpus`.

## Predictions

1. `corpus.problems()` is empty, and it is not vacuous: breaking a rule
   (outsider reply, bad parent, time going backwards, state for a user who
   cannot see the wave) is reported.
2. All 15 UI features covered by the corpus alone.
3. Every actor on every wave holds the wave's topic.
4. The HN snapshot has only the eight metadata keys; no text, no authors.
5. Loaded into SQLite, the unchanged server answers `/api/waves` per user
   with only waves that user can see.
6. No addresses other than the ten users and `public@localhost`, no hosts but
   `news.ycombinator.com`, no named real people, no deny-listed words.

## Refuted if

- covering a UI feature forces a user outside their interests (exclusivity
  and coverage conflict);
- `write_world()` cannot represent something the corpus needs (e.g. 2009
  dates before `BASE_TIME`) without editing `synthetic.py`;
- the server needs a change to serve the corpus.
