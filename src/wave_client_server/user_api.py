"""Per-user API: folders, search, read/mute/archive state, replies, tags,
participants, playback, gadget votes, contacts; plus /api/admin/*.

Maps the state-carrying elements of the 2009 Wave UI (experiments/014) onto
REST. Conversations still render over the FedOne websocket (fedone.py); this
module only adds what the FedOne protocol never carried per user.

Auth is mock-grade, HTTP Basic or a mock-login cookie:
  admin    WAVE_ADMIN_USER / WAVE_ADMIN_PASSWORD (default admin:admin), or
           any user named in WAVE_ADMINS (default alice)
  users    any known address; password = local part (alice@localhost:alice),
           or WAVE_USER_PASSWORD for all users when set.
  cookie   wave_mock_user, set by the /login dropdown (WAVE_MOCK_USERS);
           WAVE_MOCK_LOGIN=0 disables it.
Usernames may be given as the full address or the local part.

Imported at the bottom of wave_server.py, after the models exist.
"""

from __future__ import annotations

import os
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Session

from wave_client_server import fedone
from wave_client_server._version import __version__
from wave_client_server.wave_server import (
    Base,
    Wave,
    Wavelet,
    engine,
    get_db,
    manager,
)

DOMAIN = fedone.DOMAIN
PUBLIC_ADDRESS = f"public@{DOMAIN}"
FOLDERS = ["inbox", "active", "all", "by-me", "history", "spam", "trash"]
ACTIVE_WINDOW = timedelta(days=7)
GADGET_CHOICES = ("yes", "no", "maybe")

user_security = HTTPBasic(realm="wave", auto_error=False)
admin_security = HTTPBasic(realm="wave-admin", auto_error=False)


class UserWaveState(Base):
    __tablename__ = "user_wave_state"
    __table_args__ = (UniqueConstraint("user", "wave_id"),)

    id = Column(Integer, primary_key=True)
    user = Column(String, index=True, nullable=False)
    wave_id = Column(String, index=True, nullable=False)
    folder = Column(String, nullable=True)
    archived = Column(Boolean, default=False)
    muted = Column(Boolean, default=False)
    spam = Column(Boolean, default=False)
    trashed = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    tags = Column(JSON, default=list)


Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------- auth


def _unauthorized(realm: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": f'Basic realm="{realm}"'},
    )


def _equal(left: str, right: str) -> bool:
    return secrets.compare_digest(left.encode(), right.encode())


def known_users(db: Session) -> list[str]:
    addresses: set[str] = set()
    for wavelet in db.query(Wavelet).all():
        if wavelet.creator:
            addresses.add(wavelet.creator)
        addresses.update(wavelet.participants or [])
    addresses.discard(PUBLIC_ADDRESS)
    addresses.discard(f"system@{DOMAIN}")
    return sorted(addresses)


def normalize_address(username: str) -> str:
    return username if "@" in username else f"{username}@{DOMAIN}"


# Mock login: a cookie naming the user, set by the /login dropdown (web.py).
# No password, so it is as strong as the mock Basic scheme (password = name).
# WAVE_MOCK_LOGIN=0 turns it off and leaves Basic only.
MOCK_SESSION_COOKIE = "wave_mock_user"


def mock_login_enabled() -> bool:
    return os.getenv("WAVE_MOCK_LOGIN", "1") != "0"


def mock_login_users() -> list[str]:
    """Addresses offered on /login (WAVE_MOCK_USERS, default alice,bob,charlie,dave)."""
    names = os.getenv("WAVE_MOCK_USERS", "alice,bob,charlie,dave").split(",")
    return [normalize_address(name.strip()) for name in names if name.strip()]


def admin_addresses() -> set[str]:
    """Users who are also admins over all of Wave (WAVE_ADMINS, default alice)."""
    return {normalize_address(name.strip()) for name in os.getenv("WAVE_ADMINS", "alice").split(",") if name.strip()}


def is_admin(address: str) -> bool:
    return address in admin_addresses()


def basic_user(credentials: HTTPBasicCredentials, db: Session) -> str | None:
    address = normalize_address(credentials.username)
    expected = os.getenv("WAVE_USER_PASSWORD") or address.split("@", 1)[0]
    if address in known_users(db) and _equal(credentials.password, expected):
        return address
    return None


def cookie_user(request: Request, db: Session) -> str | None:
    if not mock_login_enabled():
        return None
    name = request.cookies.get(MOCK_SESSION_COOKIE)
    if not name:
        return None
    address = normalize_address(name)
    return address if address in known_users(db) else None


def signed_in_user(request: Request, credentials: HTTPBasicCredentials | None, db: Session) -> str | None:
    """Basic credentials if given (wrong ones are a 401), else the mock cookie."""
    if credentials is not None:
        address = basic_user(credentials, db)
        if address is None:
            raise _unauthorized("wave")
        return address
    return cookie_user(request, db)


def current_user(
    request: Request,
    credentials: HTTPBasicCredentials | None = Depends(user_security),
    db: Session = Depends(get_db),
) -> str:
    address = signed_in_user(request, credentials, db)
    if address is None:
        raise _unauthorized("wave")
    return address


def signed_in_admin(request: Request, credentials: HTTPBasicCredentials | None, db: Session) -> str | None:
    """admin:admin (WAVE_ADMIN_USER/PASSWORD), or a user in WAVE_ADMINS signed
    in by Basic or the mock cookie. Wrong Basic credentials are a 401."""
    if credentials is not None:
        user_ok = _equal(credentials.username, os.getenv("WAVE_ADMIN_USER", "admin"))
        password_ok = _equal(credentials.password, os.getenv("WAVE_ADMIN_PASSWORD", "admin"))
        if user_ok and password_ok:
            return credentials.username
        address = basic_user(credentials, db)
        if address is not None and is_admin(address):
            return address
        raise _unauthorized("wave-admin")
    address = cookie_user(request, db)
    return address if address is not None and is_admin(address) else None


def current_admin(
    request: Request,
    credentials: HTTPBasicCredentials | None = Depends(admin_security),
    db: Session = Depends(get_db),
) -> str:
    address = signed_in_admin(request, credentials, db)
    if address is None:
        raise _unauthorized("wave-admin")
    return address


# ---------------------------------------------------------------- models


class Participant(BaseModel):
    address: str
    name: str
    avatar: str


class WaveSummary(BaseModel):
    id: str
    title: str
    snippet: str
    creator: str
    participants: list[Participant]
    public: bool
    last_modified: datetime | None
    blip_count: int
    unread_count: int
    muted: bool
    archived: bool
    folder: str | None
    tags: list[str]


class FolderCount(BaseModel):
    name: str
    total: int
    unread: int


class Blip(BaseModel):
    id: str
    author: str
    created: datetime | None
    lines: list[str]
    unread: bool
    gadgets: list[dict[str, Any]] = Field(default_factory=list)
    children: list[Blip] = Field(default_factory=list)


class WaveView(WaveSummary):
    blips: list[Blip]


class Me(BaseModel):
    address: str
    name: str
    avatar: str
    is_admin: bool = False


class Contact(Participant):
    online: bool


class HistoryStep(BaseModel):
    step: int
    blip_id: str
    author: str
    time: datetime | None
    text: str


class NewWave(BaseModel):
    title: str
    text: str = ""
    participants: list[str] = Field(default_factory=list)


class NewBlip(BaseModel):
    text: str
    parent: str | None = Field(None, description="blip id to reply to; omit to reply to the wave")


class FolderMove(BaseModel):
    name: str | None = Field(None, description="folder name; null returns the wave to the inbox")


class TagChange(BaseModel):
    add: list[str] = Field(default_factory=list)
    remove: list[str] = Field(default_factory=list)


class ParticipantAdd(BaseModel):
    address: str


class Vote(BaseModel):
    choice: str = Field(description="yes, no or maybe")


class AdminStats(BaseModel):
    version: str
    waves: int
    wavelets: int
    users: int
    connections: dict[str, int]


class AdminUser(BaseModel):
    address: str
    waves: int
    created: int
    online: bool


# ---------------------------------------------------------------- helpers


def participant(address: str) -> Participant:
    return Participant(address=address, name=address.split("@", 1)[0], avatar=avatar_url(address))


def avatar_url(address: str) -> str:
    if address == PUBLIC_ADDRESS:
        return "/avatars/public.svg"
    return f"/avatars/{address}.svg"


def blip_id_of(wavelet: Wavelet) -> str:
    local = fedone.local_part(wavelet.wavelet_id)
    return "b+root" if local == "conv+root" else (local if local.startswith("b+") else f"b+{local}")


def wave_wavelets(db: Session) -> dict[str, list[Wavelet]]:
    grouped: dict[str, list[Wavelet]] = {}
    for wavelet in db.query(Wavelet).all():
        if wavelet.wave_id != fedone.INDEX_WAVE_ID:
            grouped.setdefault(wavelet.wave_id, []).append(wavelet)
    for wavelets in grouped.values():
        wavelets.sort(key=lambda w: (w.wavelet_id != f"{DOMAIN}!conv+root", w.creation_time or datetime.min))
    return grouped


def modified_time(wavelet: Wavelet) -> datetime | None:
    return wavelet.last_modified_time or wavelet.creation_time


def blip_unread(user: str, wavelet: Wavelet, read_at: datetime | None) -> bool:
    """Someone else wrote it after you last read the wave. Creation time, not
    modification: replies bump the root's modified time, which must not make
    the root blip unread again."""
    if wavelet.creator == user:
        return False
    return read_at is None or (wavelet.creation_time or datetime.min) > read_at


def state_for(db: Session, user: str, wave_id: str, create: bool = False) -> UserWaveState | None:
    state = db.query(UserWaveState).filter_by(user=user, wave_id=wave_id).first()
    if state is None and create:
        state = UserWaveState(user=user, wave_id=wave_id, tags=[])
        db.add(state)
        db.flush()
    return state


def lines_of(content: list[Any]) -> list[str]:
    lines: list[str] = []
    current = ""
    for item in content:
        if isinstance(item, str):
            current += item
        elif isinstance(item, dict) and item.get("type") == "line":
            if current:
                lines.append(current)
            current = ""
    if current:
        lines.append(current)
    return lines


def gadgets_of(wavelet: Wavelet) -> list[dict[str, Any]]:
    docs = wavelet.docs or {}
    votes = docs.get("gadgets", {})
    gadgets = []
    for item in docs.get("main", {}).get("content", []):
        if isinstance(item, dict) and item.get("type") == "gadget":
            attributes = item.get("attributes", {})
            gadget_id = attributes.get("id", "gadget")
            tally = votes.get(gadget_id, {})
            gadgets.append({
                "id": gadget_id,
                "kind": attributes.get("kind", "yesnomaybe"),
                "title": attributes.get("title", ""),
                "votes": {choice: tally.get(choice, []) for choice in GADGET_CHOICES},
            })
    return gadgets


def summarize(user: str, wave_id: str, wavelets: list[Wavelet], state: UserWaveState | None) -> WaveSummary:
    root = wavelets[0]
    docs = root.docs or {}
    main_lines = lines_of(docs.get("main", {}).get("content", []))
    title = fedone.plain_text(docs.get("digest", {}).get("content", [])) or (main_lines[0] if main_lines else "")
    snippet = " ".join(line for line in main_lines if line != title)[:160]
    addresses: list[str] = []
    for wavelet in wavelets:
        for address in [wavelet.creator, *(wavelet.participants or [])]:
            if address and address not in addresses:
                addresses.append(address)
    read_at = state.read_at if state else None
    unread = sum(1 for w in wavelets if blip_unread(user, w, read_at))
    times = [t for t in (modified_time(w) for w in wavelets) if t]
    return WaveSummary(
        id=wave_id,
        title=title,
        snippet=snippet,
        creator=root.creator or "",
        participants=[participant(a) for a in addresses],
        public=PUBLIC_ADDRESS in addresses,
        last_modified=max(times) if times else None,
        blip_count=len(wavelets),
        unread_count=unread,
        muted=bool(state and state.muted),
        archived=bool(state and state.archived),
        folder=state.folder if state else None,
        tags=list(state.tags or []) if state else [],
    )


def visible(user: str, summary: WaveSummary) -> bool:
    return summary.public or any(p.address == user for p in summary.participants)


def in_folder(user: str, folder: str, summary: WaveSummary, state: UserWaveState | None) -> bool:
    spam = bool(state and state.spam)
    trashed = bool(state and state.trashed)
    member = any(p.address == user for p in summary.participants)
    if folder == "spam":
        return spam
    if folder == "trash":
        return trashed
    if spam or trashed:
        return False
    if folder == "inbox":
        return member and not summary.archived and summary.folder is None
    if folder == "active":
        return member and summary.last_modified is not None and datetime.utcnow() - summary.last_modified < ACTIVE_WINDOW
    if folder == "all":
        return True
    if folder == "by-me":
        return summary.creator == user
    if folder == "history":
        return bool(state and state.read_at)
    return summary.folder == folder


def matches(query: str, summary: WaveSummary) -> bool:
    """Tokens: is:unread is:read is:muted is:public with:<name> by:<name> tag:<tag>; rest is text."""
    for token in query.split():
        key, _, value = token.partition(":")
        value = value.lower()
        if key == "is" and value == "unread":
            ok = summary.unread_count > 0
        elif key == "is" and value == "read":
            ok = summary.unread_count == 0
        elif key == "is" and value == "muted":
            ok = summary.muted
        elif key == "is" and value == "public":
            ok = summary.public
        elif key == "with" and value:
            ok = any(p.name == value or p.address == value for p in summary.participants)
        elif key == "by" and value:
            ok = summary.creator.split("@", 1)[0] == value or summary.creator == value
        elif key == "tag" and value:
            ok = value in (tag.lower() for tag in summary.tags)
        else:
            ok = token.lower() in f"{summary.title} {summary.snippet}".lower()
        if not ok:
            return False
    return True


def require_wave(db: Session, user: str, wave_id: str) -> tuple[list[Wavelet], WaveSummary]:
    wavelets = wave_wavelets(db).get(wave_id)
    if not wavelets:
        raise HTTPException(status_code=404, detail="Wave not found")
    summary = summarize(user, wave_id, wavelets, state_for(db, user, wave_id))
    if not visible(user, summary):
        raise HTTPException(status_code=404, detail="Wave not found")
    return wavelets, summary


def build_blip_tree(user: str, wavelets: list[Wavelet], read_at: datetime | None) -> list[Blip]:
    nodes: dict[str, Blip] = {}
    parents: dict[str, str | None] = {}
    order: list[str] = []
    for wavelet in wavelets:
        blip_id = blip_id_of(wavelet)
        docs = wavelet.docs or {}
        nodes[blip_id] = Blip(
            id=blip_id,
            author=wavelet.creator or "",
            created=wavelet.creation_time,
            lines=lines_of(docs.get("main", {}).get("content", [])),
            unread=blip_unread(user, wavelet, read_at),
            gadgets=gadgets_of(wavelet),
        )
        parents[blip_id] = None if blip_id == "b+root" else docs.get("thread", {}).get("parent", "b+root")
        order.append(blip_id)
    roots = []
    for blip_id in order:
        parent_id = parents[blip_id]
        if parent_id and parent_id in nodes and parent_id != blip_id:
            nodes[parent_id].children.append(nodes[blip_id])
        else:
            roots.append(nodes[blip_id])
    return roots


def touch(db: Session, wave_id: str, actor: str, when: datetime | None = None) -> datetime:
    """Record that ACTOR changed the wave: bump the root's modified time and
    version, and mark the wave read for the actor as of the same instant."""
    when = when or datetime.utcnow()
    root = db.query(Wavelet).filter_by(wave_id=wave_id, wavelet_id=f"{DOMAIN}!conv+root").first()
    if root is not None:
        root.last_modified_time = when
        root.version = (root.version or 0) + 1
    state_for(db, actor, wave_id, create=True).read_at = when
    return when


def online_users() -> dict[str, int]:
    return {client_id: len(connections) for client_id, connections in manager.active_connections.items()}


# ---------------------------------------------------------------- user routes

router = APIRouter(prefix="/api", tags=["user"])


@router.get("/me", response_model=Me)
def me(user: str = Depends(current_user)) -> Me:
    return Me(**participant(user).model_dump(), is_admin=is_admin(user))


@router.get("/folders", response_model=list[FolderCount])
def folders(user: str = Depends(current_user), db: Session = Depends(get_db)) -> list[FolderCount]:
    rows = []
    for wave_id, wavelets in wave_wavelets(db).items():
        state = state_for(db, user, wave_id)
        summary = summarize(user, wave_id, wavelets, state)
        if visible(user, summary):
            rows.append((summary, state))
    custom = sorted({s.folder for s, _ in rows if s.folder and s.folder not in FOLDERS})
    counts = []
    for name in FOLDERS + custom:
        members = [s for s, st in rows if in_folder(user, name, s, st)]
        counts.append(FolderCount(name=name, total=len(members), unread=sum(1 for s in members if s.unread_count)))
    return counts


@router.get("/waves", response_model=list[WaveSummary])
def list_waves(folder: str = "inbox", q: str = "", user: str = Depends(current_user),
               db: Session = Depends(get_db)) -> list[WaveSummary]:
    results = []
    for wave_id, wavelets in wave_wavelets(db).items():
        state = state_for(db, user, wave_id)
        summary = summarize(user, wave_id, wavelets, state)
        if visible(user, summary) and in_folder(user, folder, summary, state) and matches(q, summary):
            results.append(summary)
    results.sort(key=lambda s: s.last_modified or datetime.min, reverse=True)
    return results


@router.post("/waves", response_model=WaveSummary, status_code=201)
def create_wave(new_wave: NewWave, user: str = Depends(current_user), db: Session = Depends(get_db)) -> WaveSummary:
    wave_id = f"{DOMAIN}!w+{uuid.uuid4().hex[:8]}"
    now = datetime.utcnow()
    participants = [user] + [normalize_address(a) for a in new_wave.participants if normalize_address(a) != user]
    content: list[Any] = []
    for index, line in enumerate(new_wave.text.splitlines() or [new_wave.title]):
        if index:
            content.append({"type": "line"})
        content.append(line)
    db.add(Wave(wave_id=wave_id, creator=user, created_at=now))
    db.add(Wavelet(
        wave_id=wave_id, wavelet_id=f"{DOMAIN}!conv+root", creator=user, creation_time=now,
        last_modified_time=now, version=1, history_hash="", participants=participants,
        docs={"main": {"docId": "main", "contributors": [user], "content": content},
              "digest": {"docId": "digest", "contributors": [user], "content": [new_wave.title]}},
    ))
    db.flush()
    state = state_for(db, user, wave_id, create=True)
    state.read_at = now
    db.commit()
    wavelets = wave_wavelets(db)[wave_id]
    return summarize(user, wave_id, wavelets, state)


@router.get("/waves/{wave_id}/view", response_model=WaveView)
def view_wave(wave_id: str, user: str = Depends(current_user), db: Session = Depends(get_db)) -> WaveView:
    wavelets, summary = require_wave(db, user, wave_id)
    state = state_for(db, user, wave_id)
    return WaveView(**summary.model_dump(), blips=build_blip_tree(user, wavelets, state.read_at if state else None))


def _set_state(db: Session, user: str, wave_id: str, **changes: Any) -> WaveSummary:
    require_wave(db, user, wave_id)
    state = state_for(db, user, wave_id, create=True)
    for key, value in changes.items():
        setattr(state, key, value)
    db.commit()
    return summarize(user, wave_id, wave_wavelets(db)[wave_id], state)


@router.post("/waves/{wave_id}/read", response_model=WaveSummary)
def mark_read(wave_id: str, user: str = Depends(current_user), db: Session = Depends(get_db)) -> WaveSummary:
    return _set_state(db, user, wave_id, read_at=datetime.utcnow())


@router.post("/waves/{wave_id}/unread", response_model=WaveSummary)
def mark_unread(wave_id: str, user: str = Depends(current_user), db: Session = Depends(get_db)) -> WaveSummary:
    return _set_state(db, user, wave_id, read_at=None)


@router.post("/waves/{wave_id}/archive", response_model=WaveSummary)
def archive(wave_id: str, user: str = Depends(current_user), db: Session = Depends(get_db)) -> WaveSummary:
    return _set_state(db, user, wave_id, archived=True)


@router.post("/waves/{wave_id}/unarchive", response_model=WaveSummary)
def unarchive(wave_id: str, user: str = Depends(current_user), db: Session = Depends(get_db)) -> WaveSummary:
    return _set_state(db, user, wave_id, archived=False)


@router.post("/waves/{wave_id}/mute", response_model=WaveSummary)
def mute(wave_id: str, user: str = Depends(current_user), db: Session = Depends(get_db)) -> WaveSummary:
    return _set_state(db, user, wave_id, muted=True, archived=True)


@router.post("/waves/{wave_id}/unmute", response_model=WaveSummary)
def unmute(wave_id: str, user: str = Depends(current_user), db: Session = Depends(get_db)) -> WaveSummary:
    return _set_state(db, user, wave_id, muted=False)


@router.post("/waves/{wave_id}/spam", response_model=WaveSummary)
def report_spam(wave_id: str, user: str = Depends(current_user), db: Session = Depends(get_db)) -> WaveSummary:
    return _set_state(db, user, wave_id, spam=True)


@router.post("/waves/{wave_id}/trash", response_model=WaveSummary)
def trash(wave_id: str, user: str = Depends(current_user), db: Session = Depends(get_db)) -> WaveSummary:
    return _set_state(db, user, wave_id, trashed=True)


@router.post("/waves/{wave_id}/restore", response_model=WaveSummary)
def restore(wave_id: str, user: str = Depends(current_user), db: Session = Depends(get_db)) -> WaveSummary:
    return _set_state(db, user, wave_id, trashed=False, spam=False, archived=False, folder=None)


@router.post("/waves/{wave_id}/folder", response_model=WaveSummary)
def move_to_folder(wave_id: str, move: FolderMove, user: str = Depends(current_user),
                   db: Session = Depends(get_db)) -> WaveSummary:
    if move.name in FOLDERS:
        raise HTTPException(status_code=422, detail=f"{move.name} is a system folder")
    return _set_state(db, user, wave_id, folder=move.name or None)


@router.post("/waves/{wave_id}/tags", response_model=WaveSummary)
def change_tags(wave_id: str, change: TagChange, user: str = Depends(current_user),
                db: Session = Depends(get_db)) -> WaveSummary:
    require_wave(db, user, wave_id)
    state = state_for(db, user, wave_id, create=True)
    tags = [t for t in (state.tags or []) if t not in change.remove]
    tags += [t for t in change.add if t and t not in tags]
    return _set_state(db, user, wave_id, tags=tags)


@router.post("/waves/{wave_id}/participants", response_model=WaveSummary)
def add_participant(wave_id: str, addition: ParticipantAdd, user: str = Depends(current_user),
                    db: Session = Depends(get_db)) -> WaveSummary:
    wavelets, _ = require_wave(db, user, wave_id)
    address = normalize_address(addition.address)
    root = wavelets[0]
    if address not in (root.participants or []):
        root.participants = [*(root.participants or []), address]
        touch(db, wave_id, user)
    db.commit()
    return summarize(user, wave_id, wave_wavelets(db)[wave_id], state_for(db, user, wave_id))


@router.post("/waves/{wave_id}/blips", response_model=Blip, status_code=201)
def reply(wave_id: str, new_blip: NewBlip, user: str = Depends(current_user),
          db: Session = Depends(get_db)) -> Blip:
    wavelets, _ = require_wave(db, user, wave_id)
    existing = {blip_id_of(w) for w in wavelets}
    parent = new_blip.parent or "b+root"
    if parent not in existing:
        raise HTTPException(status_code=422, detail=f"No blip {parent} in {wave_id}")
    blip_id = f"b+{uuid.uuid4().hex[:8]}"
    now = datetime.utcnow()
    content: list[Any] = []
    for index, line in enumerate(new_blip.text.splitlines() or [""]):
        if index:
            content.append({"type": "line"})
        content.append(line)
    db.add(Wavelet(
        wave_id=wave_id, wavelet_id=f"{DOMAIN}!{blip_id}", creator=user, creation_time=now,
        last_modified_time=now, version=1, history_hash="", participants=[user],
        docs={"main": {"docId": "main", "contributors": [user], "content": content},
              "thread": {"parent": parent}},
    ))
    touch(db, wave_id, user, now)
    db.commit()
    return Blip(id=blip_id, author=user, created=now, lines=lines_of(content), unread=False)


@router.get("/waves/{wave_id}/history", response_model=list[HistoryStep])
def playback(wave_id: str, user: str = Depends(current_user), db: Session = Depends(get_db)) -> list[HistoryStep]:
    wavelets, _ = require_wave(db, user, wave_id)
    ordered = sorted(wavelets, key=lambda w: w.creation_time or datetime.min)
    return [
        HistoryStep(step=index + 1, blip_id=blip_id_of(w), author=w.creator or "", time=w.creation_time,
                    text=" / ".join(lines_of((w.docs or {}).get("main", {}).get("content", []))))
        for index, w in enumerate(ordered)
    ]


@router.post("/waves/{wave_id}/gadgets/{gadget_id}/vote", response_model=list[dict[str, Any]])
def vote(wave_id: str, gadget_id: str, ballot: Vote, user: str = Depends(current_user),
         db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    if ballot.choice not in GADGET_CHOICES:
        raise HTTPException(status_code=422, detail=f"choice must be one of {', '.join(GADGET_CHOICES)}")
    wavelets, _ = require_wave(db, user, wave_id)
    for wavelet in wavelets:
        if any(g["id"] == gadget_id for g in gadgets_of(wavelet)):
            docs = dict(wavelet.docs or {})
            votes = {k: dict(v) for k, v in docs.get("gadgets", {}).items()}
            tally = {choice: [a for a in votes.get(gadget_id, {}).get(choice, []) if a != user]
                     for choice in GADGET_CHOICES}
            tally[ballot.choice].append(user)
            votes[gadget_id] = tally
            docs["gadgets"] = votes
            wavelet.docs = docs
            touch(db, wave_id, user)
            db.commit()
            return gadgets_of(wavelet)
    raise HTTPException(status_code=404, detail=f"No gadget {gadget_id} in {wave_id}")


@router.get("/contacts", response_model=list[Contact])
def contacts(user: str = Depends(current_user), db: Session = Depends(get_db)) -> list[Contact]:
    online = online_users()
    return [Contact(**participant(a).model_dump(), online=a in online) for a in known_users(db) if a != user]


# ---------------------------------------------------------------- admin routes

admin_router = APIRouter(prefix="/api/admin", tags=["admin"])


@admin_router.get("/stats", response_model=AdminStats)
def admin_stats(_: str = Depends(current_admin), db: Session = Depends(get_db)) -> AdminStats:
    return AdminStats(
        version=__version__,
        waves=len(wave_wavelets(db)),
        wavelets=db.query(Wavelet).count(),
        users=len(known_users(db)),
        connections=online_users(),
    )


@admin_router.get("/users", response_model=list[AdminUser])
def admin_users(_: str = Depends(current_admin), db: Session = Depends(get_db)) -> list[AdminUser]:
    grouped = wave_wavelets(db)
    online = online_users()
    users = []
    for address in known_users(db):
        member_of = [wid for wid, ws in grouped.items()
                     if any(address == w.creator or address in (w.participants or []) for w in ws)]
        created = [wid for wid, ws in grouped.items() if ws[0].creator == address]
        users.append(AdminUser(address=address, waves=len(member_of), created=len(created), online=address in online))
    return users


@admin_router.get("/waves", response_model=list[WaveSummary])
def admin_waves(_: str = Depends(current_admin), db: Session = Depends(get_db)) -> list[WaveSummary]:
    summaries = [summarize("", wid, ws, None) for wid, ws in wave_wavelets(db).items()]
    return sorted(summaries, key=lambda s: s.last_modified or datetime.min, reverse=True)


@admin_router.get("/waves/{wave_id}", response_model=list[dict[str, Any]])
def admin_wave_raw(wave_id: str, _: str = Depends(current_admin), db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    wavelets = wave_wavelets(db).get(wave_id)
    if not wavelets:
        raise HTTPException(status_code=404, detail="Wave not found")
    return [
        {"wavelet_id": w.wavelet_id, "creator": w.creator, "version": w.version,
         "created": w.creation_time.isoformat() if w.creation_time else None,
         "participants": w.participants, "docs": w.docs}
        for w in wavelets
    ]
