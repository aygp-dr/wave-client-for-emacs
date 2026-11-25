# 015 — Browser views: /admin and /app in ClojureScript via scittle

Follows 014, which built the per-user and admin REST API and promised "the
same API serves a ClojureScript (scittle, no build step) `/admin` view and
logged-in user view". This experiment builds those two views.

## Conjecture

Both views can be written as one `.cljs` file each, interpreted in the
browser by scittle from a pinned CDN, served by the existing FastAPI app
with no build step and no new Python dependency, and using only the routes
`user_api.py` already exposes. HTTP Basic on the page route itself is enough
auth: the browser prompts once on `GET /app` (realm `wave`) or `GET /admin`
(realm `wave-admin`) and then sends the same credentials on the page's
same-origin `fetch` calls, so the pages never see or store a password.

## Design

- `web.py`: one router, `include_router`-ed at the bottom of
  `wave_server.py`. `GET /admin` depends on `current_admin`, `GET /app` on
  `current_user`; both return `web/<page>.html`. `GET /web/<file>.cljs`
  serves the sources (no secrets in them, so unauthenticated).
- Rendering: scittle 0.8.33 + its replicant plugin (pure-ClojureScript
  hiccup renderer, no React), so there is no React 18 `ReactDOM.render`
  deprecation error on the console.
- `/app`: three panes after the 2009 client (014 element map): folders +
  contacts | wave list (unread badge, avatars, title — snippet, time, N
  msgs) | open wave (participants, public banner, threaded blips, Yes/No/Maybe
  table with vote buttons, reply box, tags, archive/mute/read/unread/spam/
  trash). Every action re-fetches the list and the open wave; a 10 s poll
  keeps both fresh.
- `/admin`: version + health, stats, users table, waves table; clicking a
  wave shows `/api/admin/waves/{id}` as pretty JSON.

## Predictions

1. `GET /app` and `GET /admin` answer 401 with `WWW-Authenticate: Basic
   realm="wave"` / `realm="wave-admin"` without credentials and with wrong
   ones, 200 HTML with right ones; user credentials on `/admin` are 401.
2. In Chrome, loading `http://erin:erin@localhost:9896/app` renders the
   three panes with zero console errors, and the page's `fetch` calls
   succeed without the page knowing the password.
3. Clicking a wave marks it read (its unread badge disappears after the
   re-fetch); voting on a gadget moves the voter's avatar into the chosen
   column; posting a reply adds a blip nested under its parent.
4. `/admin` renders stats, users and waves; clicking a wave shows raw
   wavelet JSON with `docs`.
5. No change to `user_api.py` is needed, and the `wave_server.py` change is
   one import plus one `include_router`.

## Refuted if

- the browser does not reuse page credentials for `fetch` (then pages would
  need a login form and a token, i.e. the auth design is wrong);
- any view needs an endpoint `user_api.py` lacks (014's API shape is
  incomplete for a browser client);
- scittle needs a build step or a non-CDN asset to work.
