"""Browser views: /admin and /app, ClojureScript run in the page by scittle.

The page routes themselves require HTTP Basic (realm wave-admin for /admin,
wave for /app), so the browser prompts on first load and then resends the
same credentials on the page's same-origin fetch calls to /api/... The pages
never see or store a password.

The .cljs sources hold no secrets and are served without auth from /web/.
Imported at the bottom of wave_server.py, after user_api.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from wave_client_server.user_api import current_admin, current_user

WEB_DIR = Path(__file__).resolve().parent / "web"
SOURCE_FILES = {"admin.cljs", "app.cljs", "wave.css"}
SOURCE_MEDIA_TYPES = {".cljs": "application/x-scittle", ".css": "text/css"}
NO_STORE = {"Cache-Control": "no-store"}

router = APIRouter(include_in_schema=False)


def page(name: str) -> HTMLResponse:
    return HTMLResponse((WEB_DIR / name).read_text(encoding="utf-8"), headers=NO_STORE)


@router.get("/admin", response_class=HTMLResponse)
def admin_page(_: str = Depends(current_admin)) -> HTMLResponse:
    return page("admin.html")


@router.get("/app", response_class=HTMLResponse)
def app_page(_: str = Depends(current_user)) -> HTMLResponse:
    return page("app.html")


@router.get("/web/{file_name}")
def web_source(file_name: str) -> FileResponse:
    if file_name not in SOURCE_FILES:
        raise HTTPException(status_code=404, detail="Not found")
    source_path = WEB_DIR / file_name
    return FileResponse(source_path, media_type=SOURCE_MEDIA_TYPES[source_path.suffix], headers=NO_STORE)
