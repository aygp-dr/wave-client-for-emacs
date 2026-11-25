# 014 — Wave UI parity: per-user API, Emacs navigation, /admin and user views

Reference: two 2009 Google Wave screenshots in `reference/google-wave-ui/`
(gitignored, third-party). One is the three-pane client (navigation, wave
list, open wave); the other is a public wave with a Yes/No/Maybe gadget.

## Conjecture

Every element in those screenshots that carries *state or navigation* (not
chrome) maps to (a) one per-user REST operation on the Python server and
(b) one key or line in the Emacs client, without changing the FedOne
websocket path that renders conversations (009/010). The same API serves
a ClojureScript (scittle, no build step) `/admin` view and logged-in user
view.

## Element map

| screenshot element | server (Python) | Emacs |
|---|---|---|
| Navigation: Inbox, Active, All, By Me, History, Spam, Trash | `GET /api/folders` (counts), `GET /api/waves?folder=` | header-line tabs in `*Wave List*`; `f` choose folder, `1`–`7` direct |
| Searches (+Add), search box | `GET /api/waves?q=` (`is:unread with:bob tag:x` + text) | `s` search, `S` save search (local) |
| Folders (+Add) | `POST /api/waves/{id}/folder` | `F` move to folder |
| Contacts (online dot) | `GET /api/contacts` (online = open websocket) | `C` contacts buffer; `RET` new wave with contact |
| New Wave | `POST /api/waves` | `c` compose |
| Toolbar: Archive, Mute, Read, Unread, Spam | `POST /api/waves/{id}/{archive,mute,read,unread,spam,trash}` | `a` `m` `r` `u` `!` `D` in list and wave |
| Row: avatars, title — snippet, time, N msgs, unread badge | `WaveSummary` fields | columns: unread, participants, title — snippet (shadow), time, msgs |
| Wave header: participant strip, +Add | `POST /api/waves/{id}/participants` | header line; `+` add participant |
| "Everyone has access" banner | `public` flag (participant `public@localhost`) | banner line |
| Reply / threaded replies | `POST /api/waves/{id}/blips {parent, text}`; manifest `<thread>` nesting | `R` reply to wave, `i` reply to blip; indent per thread |
| Playback | `GET /api/waves/{id}/history` | `v` playback buffer, `,` / `.` step |
| Tags | `POST /api/waves/{id}/tags` | tags line; `t` add, `T` remove |
| Yes/No/Maybe gadget | `<gadget>` element in blip; `POST …/gadgets/{gid}/vote` | three-column table; `y` `n` `?` vote |
| Avatars | `/avatars/*` (resources/avatars, manifest.json) | inline SVG when `display-images-p` |
| Signed-in user | `GET /api/me` | mode line |

Auth: HTTP Basic. `admin:admin` for `/admin` and `/api/admin/*`; mock users
`<local-part>:<local-part>` (dev only; env overrides). Existing public routes
(`/`, `/health`, `/api/inbox`, `/api/waves/{id}`, `/ws`) stay open.

## Predictions

1. The API is expressible without breaking the 009/010 path: `gmake
   elisp-list-waves` and the existing tests keep passing.
2. Read state round-trips: marking a wave read via REST zeroes its unread
   count in both `/api/waves?folder=inbox` and the Emacs list.
3. A reply posted from Emacs appears, nested under its parent blip, in the
   next websocket open of that wave (fedone emits `<thread>` nesting).
4. restish discovers every new operation from `/openapi.json`.

## Refuted if

- any element needs the websocket protocol changed (then the split REST/WS
  design is wrong);
- the Emacs list needs a second round-trip per row (API shape is wrong).
