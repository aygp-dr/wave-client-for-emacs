# 015 — Proof: /admin and /app in scittle

Built: `src/wave_client_server/web.py` (router), `web/{app,admin}.{html,cljs}`,
`web/wave.css`, `tests/test_web_views.py`. `wave_server.py` gained one import
and one `include_router`; `user_api.py` is unchanged.

Rendering: scittle 0.8.33 (newest on npm, published 2026-08-18) with its
replicant plugin. Replicant renders hiccup without React; scittle's reagent
plugin has no `reagent.dom.client`, so with React 18 it would log the
`ReactDOM.render is no longer supported` error on every load.

## Results

| # | prediction | result |
|---|---|---|
| 1 | 401/401/200 matrix, realm per page, user creds on /admin → 401 | **held** — `tests/test_web_views.py`; `26 passed` with test_user_api.py |
| 2 | Chrome renders /app via `http://erin:erin@…` with zero console errors; fetches authenticate | **held** — 0 console messages on /app and /admin (incl. no 4xx responses, no failed requests) |
| 3 | open clears unread badge; vote moves avatar; reply nests under parent | **held** — see below |
| 4 | /admin shows stats, users, waves; click shows raw wavelets with `docs` | **held** — 18 waves, 17 users, 9 raw wavelets incl. the reply posted from /app |
| 5 | no user_api.py change; wave_server.py change is import + include | **held** |

Browser run (`browser_check.py`, output in `browser_report.json`), against a
fresh `gen-synthetic-waves.py --seed 1` DB on port 9896:

- open `localhost!w+g2x4` from the inbox: row `wave-row unread` with badge
  `7` → 7 blips highlighted unread in the open wave → after the auto
  mark-read, row `wave-row selected`, no badge.
- vote Yes on gadget `poll` in `b+g2x4r3`: header `Yes (0) No (3) Maybe (0)`
  → `Yes (1) No (2) Maybe (0)`; Yes column holds `erin@localhost` (erin's
  earlier No moved, as the API replaces a voter's previous choice).
- reply to `b+g2x4r3`: the new blip renders inside that blip's `.thread`.
- Archive removes the wave from the inbox list; Unarchive brings it back.
- `/admin` with `admin:admin`: version 0.2.1, healthy, 18 waves, 99
  wavelets, 17 users, 0 connections.
- `erin:erin` on `/admin`: Chrome aborts with `ERR_INVALID_AUTH_CREDENTIALS`
  (its handling of a 401 to URL-supplied credentials).
- Server log: no `Authorization` value or `user:pass` string appears.

Screenshots: `docs/screenshots/web-app.png`, `docs/screenshots/web-admin.png`.

## Deviations and what was not shown

- **Tool deviation.** The chrome-devtools MCP could not start: its Chrome
  profile was held by another session's browser, and stopping that was not
  ours to do. The check ran instead with Playwright driving the system
  Chrome (158, headless, throwaway profile). Same engine; different driver.
- `location.href` came back without userinfo, so Chrome strips it after
  navigation. Building fetch URLs from `location.origin` is therefore a
  precaution, not something this run proved necessary.
- Not exercised in the browser: tags, add participant, new wave, mute,
  spam/trash/restore, search, contact click, the 10 s poll. They call the
  same `request` helper and `user_api` routes that test_user_api.py covers,
  but no browser run shows them working.
- Credentials are shared per origin: a browser holding admin credentials
  for `/` will send them to `/api/...`, where the user realm rejects them
  and Chrome prompts again. Use separate profiles for admin and user.
