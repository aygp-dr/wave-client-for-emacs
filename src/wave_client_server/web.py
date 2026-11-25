"""Browser views: /login, /admin and /app; the last two are ClojureScript
run in the page by scittle.

Signing in is either HTTP Basic (realm wave-admin for /admin, wave for /app)
or, unless WAVE_MOCK_LOGIN=0, the /login page: a dropdown of mock users
(WAVE_MOCK_USERS) that sets the wave_mock_user cookie. Without either, the
pages redirect to /login (or, with mock login off, answer a Basic challenge).
The page's same-origin fetch calls to /api/... carry whichever was used, so
the pages never see or store a password.

The .cljs sources hold no secrets and are served without auth from /web/.
Imported at the bottom of wave_server.py, after user_api.
"""

from __future__ import annotations

import html
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.security import HTTPBasicCredentials
from sqlalchemy.orm import Session

from wave_client_server.user_api import (
    MOCK_SESSION_COOKIE,
    _unauthorized,
    admin_security,
    cookie_user,
    is_admin,
    known_users,
    mock_login_enabled,
    mock_login_users,
    normalize_address,
    signed_in_admin,
    signed_in_user,
    user_security,
)
from wave_client_server.wave_server import get_db

WEB_DIR = Path(__file__).resolve().parent / "web"
SOURCE_FILES = {"admin.cljs", "app.cljs", "wave.css"}
SOURCE_MEDIA_TYPES = {".cljs": "application/x-scittle", ".css": "text/css"}
NO_STORE = {"Cache-Control": "no-store"}
LOGIN_ERRORS = {
    "unknown": "That user is not on the mock login list.",
    "not-admin": "Admin needs a Wave admin; sign in as one.",
}

router = APIRouter(include_in_schema=False)


def page(name: str) -> HTMLResponse:
    return HTMLResponse((WEB_DIR / name).read_text(encoding="utf-8"), headers=NO_STORE)


def to_login(error: str | None = None) -> RedirectResponse:
    return RedirectResponse("/login" + (f"?error={error}" if error else ""), status_code=303, headers=NO_STORE)


@router.get("/admin", response_class=HTMLResponse)
def admin_page(
    request: Request,
    credentials: HTTPBasicCredentials | None = Depends(admin_security),
    db: Session = Depends(get_db),
) -> Response:
    if signed_in_admin(request, credentials, db) is not None:
        return page("admin.html")
    if not mock_login_enabled():
        raise _unauthorized("wave-admin")
    return to_login("not-admin" if cookie_user(request, db) else None)


@router.get("/app", response_class=HTMLResponse)
def app_page(
    request: Request,
    credentials: HTTPBasicCredentials | None = Depends(user_security),
    db: Session = Depends(get_db),
) -> Response:
    if signed_in_user(request, credentials, db) is not None:
        return page("app.html")
    if not mock_login_enabled():
        raise _unauthorized("wave")
    return to_login()


def login_choices(db: Session) -> list[str]:
    known = set(known_users(db))
    return [address for address in mock_login_users() if address in known]


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str | None = None, db: Session = Depends(get_db)) -> HTMLResponse:
    if not mock_login_enabled():
        raise HTTPException(status_code=404, detail="Not found")
    current = cookie_user(request, db)
    options = "\n".join(
        f'<option value="{html.escape(address)}"{" selected" if address == current else ""}>'
        f'{html.escape(address.split("@")[0])}{" (admin)" if is_admin(address) else ""}</option>'
        for address in login_choices(db)
    )
    status_line = (
        f'<p class="signed-in">Signed in as {html.escape(current)}. '
        f'<a href="/app">Open Wave</a> · <a href="/logout">Sign out</a></p>'
        if current else '<p class="signed-in">Not signed in.</p>'
    )
    error_line = f'<p class="error">{html.escape(LOGIN_ERRORS.get(error or "", ""))}</p>' if error in LOGIN_ERRORS else ""
    body = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Wave sign in</title>
  <link rel="icon" href="data:,">
  <link rel="stylesheet" href="/web/wave.css">
</head>
<body class="login-page">
  <form class="login" method="post" action="/login">
    <h1>Wave</h1>
    {status_line}
    {error_line}
    <label for="user">Sign in as</label>
    <select id="user" name="user">
{options}
    </select>
    <div class="login-actions">
      <button type="submit" name="to" value="/app">Open Wave</button>
      <button type="submit" name="to" value="/admin">Admin</button>
    </div>
    <p class="hint">Mock login: no password. Basic auth (name:name, admin:admin) still works.</p>
  </form>
</body>
</html>"""
    return HTMLResponse(body, headers=NO_STORE)


@router.post("/login")
async def login_submit(request: Request, db: Session = Depends(get_db)) -> RedirectResponse:
    if not mock_login_enabled():
        raise HTTPException(status_code=404, detail="Not found")
    form = parse_qs((await request.body()).decode("utf-8"))
    address = normalize_address((form.get("user") or [""])[0])
    destination = (form.get("to") or ["/app"])[0]
    if address not in login_choices(db):
        return to_login("unknown")
    if destination == "/admin" and not is_admin(address):
        destination = "/login?error=not-admin"
    elif destination not in ("/app", "/admin"):
        destination = "/app"
    response = RedirectResponse(destination, status_code=303, headers=NO_STORE)
    response.set_cookie(MOCK_SESSION_COOKIE, address.split("@")[0], httponly=True, samesite="lax", path="/")
    return response


@router.get("/logout")
def logout() -> RedirectResponse:
    response = to_login()
    response.delete_cookie(MOCK_SESSION_COOKIE, path="/")
    return response


@router.get("/web/{file_name}")
def web_source(file_name: str) -> FileResponse:
    if file_name not in SOURCE_FILES:
        raise HTTPException(status_code=404, detail="Not found")
    source_path = WEB_DIR / file_name
    return FileResponse(source_path, media_type=SOURCE_MEDIA_TYPES[source_path.suffix], headers=NO_STORE)
