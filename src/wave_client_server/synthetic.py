"""Synthetic Wave worlds: Hypothesis strategies for *valid* data, a writer
that puts a world into the database, and the UI-coverage checklist.

Used three ways:
- property tests (tests/test_properties.py) draw worlds and check API and
  FedOne invariants on each;
- scripts/gen-synthetic-waves.py draws seeded, reproducible worlds into a
  database to drive the Emacs client and web views;
- UI_FEATURES says which client states a dataset exercises, so "enough data
  to drive the UI" is a checked property rather than a hope.

Validity rules the strategies enforce by construction:
- a reply's parent is an earlier blip of the same wave;
- authors and voters are participants of the wave;
- each voter appears in at most one gadget column;
- per-user state only exists for users who can see the wave;
- timestamps increase within a wave.

Needs the `test` extra (hypothesis).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from hypothesis import strategies as st

DOMAIN = "localhost"
PUBLIC = f"public@{DOMAIN}"
NAMES = ["alice", "bob", "charlie", "dave", "erin", "frank", "grace", "heidi", "ivan", "judy",
         "mallory", "niaj", "olivia", "peggy", "rupert", "sybil", "trent", "victor", "walter"]
BASE_TIME = datetime(2026, 1, 1, 9, 0, 0)


@dataclass(frozen=True)
class Theme:
    """A kind of conversation Wave users had in 2009-2010.

    Titles are what a creator would call the wave; the opener is the rest of
    the root blip; the chain is the conversation in order, so the n-th reply
    of a wave says the n-th thing and threads read as a discussion rather
    than word salad. Dates put the wave in its era."""
    name: str
    start: datetime
    titles: tuple[str, ...]
    opener: tuple[str, ...]
    chain: tuple[str, ...]


THEMES: tuple[Theme, ...] = (
    Theme(
        "io2010-live", datetime(2010, 5, 19, 9, 0),
        titles=(
            "Live Wave: Developing with HTML5 Wednesday May 19, at 3:00pm-4:00pm, Room #5 (More Info)",
            "Live Wave: Measure in milliseconds redux: Meet Speed Tracer Wednesday May 19, at 10:45am-11:45am",
            "Live Wave: How Google builds APIs",
            "Live Wave: BigQuery and Prediction APIs",
            "Live Wave: Google Charts Toolkit: a unified approach for creating dynamic charts on the web",
            "Live Wave: Beyond design: Creating positive user experiences",
            "Google I/O 2010: Opening up Closure Library",
        ),
        opener=(
            "This is the official live wave for the session.",
            "Add questions as replies; the speakers will take them at the end.",
            "Slides and video will be posted after the conference.",
        ),
        chain=(
            "Session starting now, room is packed.",
            "Is there a video of this one for those of us not in Moscone?",
            "Q: will the API be open to everyone, or invite only for now?",
            "+1 to that question",
            "They said invite only during the preview, open later this year.",
            "Slides link please?",
            "Posted on the session page, see the More Info link.",
            "Great demo. Does this work offline?",
            "The offline answer was: not yet, but they are looking at it.",
            "Thanks all, see you at the after party.",
        ),
    ),
    Theme(
        "sandbox-2009", datetime(2009, 6, 1, 10, 0),
        titles=(
            "So how was Google I/O for you?",
            "Who has invites left?",
            "Wave sandbox: anyone else seeing playback lag on long waves?",
            "New to Wave: anyone want to go through the features?",
            "Wave etiquette: when do you reply inline vs at the bottom?",
        ),
        opener=(
            "Looking for fellow sandbox account holders who want to get some waves going.",
            "I got my sandbox account after the keynote and have no contacts yet.",
        ),
        chain=(
            "I suppose they will not mind if we just started adding them.",
            "It really is like email if it were invented today.",
            "Watching other people type in real time is the strangest part.",
            "Firefox gets slow once a wave passes a couple of hundred blips.",
            "Chrome is much faster with it.",
            "Try playback on this wave, it is fun to watch it grow.",
            "The developer preview opens to 100,000 people on September 30.",
            "I have 8 invites, reply here with your address.",
            "Inline replies get confusing after the third level.",
        ),
    ),
    Theme(
        "fedone", datetime(2009, 7, 22, 14, 0),
        titles=(
            "FedOne: build from hg trunk fails with ant",
            "Federating with wavesandbox.com over XMPP",
            "Running the FedOne reference server behind Openfire",
            "Is anyone running Wave in a Box in production?",
        ),
        opener=(
            "Followed the getting-started page, the server starts but the client cannot connect.",
            "Logs below.",
        ),
        chain=(
            "Which Java version? It needs Java 6.",
            "The server runs as an XMPP external component, so check the component port in Openfire.",
            "The certificate has to match the domain you federate as.",
            "run-server.sh first, then run-client-console.sh with your user@domain.",
            "That fixed it, the console client sees my waves now.",
            "Federating with the sandbox needs an allow-list entry on their side.",
            "The websocket client branch is newer than the console client, try that.",
            "Pinning to an older hg revision avoids the protocol change from last week.",
        ),
    ),
    Theme(
        "emacs-client", datetime(2010, 8, 1, 20, 0),
        titles=(
            "Emacs Wave client: websocket mode",
            "M-x wave-list shows nothing",
            "Rendering blips with ewoc in the Emacs client",
            "Emacs client: reply support?",
        ),
        opener=(
            "The Emacs client talks to a FedOne server over a websocket.",
            "Load wave-client.el and run M-x wave-list.",
        ),
        chain=(
            "Set wave-client-connection-method to websocket first.",
            "It needs a FedOne server from the August 2010 revisions; newer ones changed the wire format.",
            "Works for me on Emacs 23.1.",
            "Blips render with ewoc, one node per blip.",
            "The unread count comes from the index wave.",
            "Replies are read-only for now, the submit side is not wired up.",
            "Patches welcome, it is all on code.google.com.",
        ),
    ),
    Theme(
        "robots-gadgets", datetime(2010, 2, 8, 11, 0),
        titles=(
            "Friday lunch: who is in?",
            "Writing a robot on App Engine with the Robots API v2",
            "My robot keeps replying to itself",
            "Gadget state: shared per wave or per user?",
        ),
        opener=(
            "Vote with the gadget below.",
            "Robot code is on appspot, capabilities are declared in the robot's profile.",
        ),
        chain=(
            "In, as long as it is not the same place as last week.",
            "Maybe, depends on the release.",
            "The robot gets a BLIP_SUBMITTED event for its own blips too, filter on the author.",
            "Gadget state is shared by everyone on the wave.",
            "Use the participant id as the key if you want per-user state.",
            "v2 lets the robot reply in the same request, no more proxying.",
            "Count me out, deadline Friday.",
        ),
    ),
    Theme(
        "end-of-wave", datetime(2010, 8, 4, 18, 0),
        titles=(
            "Google stops developing Wave as a standalone product",
            "Export your waves before the shutdown",
            "Wave goes to Apache: what happens to FedOne?",
        ),
        opener=(
            "Announced today on the official blog.",
            "The site stays up through the end of the year.",
        ),
        chain=(
            "Did not see that coming after I/O.",
            "The protocol and FedOne are open source, so the code lives on.",
            "Export to PDF works per wave; there is no bulk export yet.",
            "Wave in a Box is going to the Apache incubator.",
            "I will keep the Emacs client running against a local server.",
            "Concurrent editing will show up in other products.",
        ),
    ),
)
THEMES_BY_NAME = {theme.name: theme for theme in THEMES}


@dataclass
class BlipSpec:
    blip_id: str
    author: str
    parent: str | None          # None only for b+root
    lines: list[str]
    minutes: int                 # offset from the wave's start
    gadget: dict[str, list[str]] | None = None  # choice -> voters


@dataclass
class WaveSpec:
    wave_id: str
    creator: str
    title: str
    participants: list[str]
    blips: list[BlipSpec]
    start_minutes: int
    era_start: datetime = BASE_TIME  # the theme's date; blips count from here


@dataclass
class StateSpec:
    user: str
    wave_id: str
    folder: str | None = None
    archived: bool = False
    muted: bool = False
    spam: bool = False
    trashed: bool = False
    read_after_blips: int | None = None  # read once this many blips existed
    tags: list[str] = field(default_factory=list)


@dataclass
class World:
    users: list[str]
    waves: list[WaveSpec]
    states: list[StateSpec]


# ---------------------------------------------------------------- strategies

def unicode_text() -> st.SearchStrategy[str]:
    printable = st.characters(blacklist_categories=("Cs", "Cc", "Co", "Cn"))
    return st.text(printable, min_size=1, max_size=120).map(str.strip).filter(bool)


def themed(lines: st.SearchStrategy[str], edgy: bool) -> st.SearchStrategy[str]:
    """A theme's line, or (edgy) sometimes arbitrary printable unicode."""
    return st.one_of(lines, unicode_text()) if edgy else lines


def chain_lines(theme: Theme, number: int, count: int) -> list[str]:
    """COUNT consecutive lines of THEME's conversation, starting at reply NUMBER."""
    return [theme.chain[(number + offset) % len(theme.chain)] for offset in range(count)]


@st.composite
def wave_specs(draw: st.DrawFn, index: int, users: list[str], edgy: bool, prefix: str = "s") -> WaveSpec:
    theme = draw(st.sampled_from(THEMES))
    creator = draw(st.sampled_from(users))
    others = [u for u in users if u != creator]
    invited = draw(st.lists(st.sampled_from(others), unique=True, max_size=len(others))) if others else []
    participants = [creator, *invited]
    if draw(st.integers(0, 4)) == 0:
        participants.append(PUBLIC)
    authors = [p for p in participants if p != PUBLIC]

    title = draw(themed(st.sampled_from(theme.titles), edgy))
    opener = draw(st.lists(themed(st.sampled_from(theme.opener), edgy), max_size=3))
    root = BlipSpec("b+root", creator, None, [title, *opener], 0)
    blips = [root]
    for number in range(draw(st.integers(0, 7))):
        parent = draw(st.sampled_from([b.blip_id for b in blips]))
        lines = chain_lines(theme, number, draw(st.integers(1, 3)))
        if edgy and draw(st.booleans()):
            lines[0] = draw(unicode_text())
        blips.append(BlipSpec(f"b+{prefix}{index}r{number}", draw(st.sampled_from(authors)), parent,
                              lines, 5 * (number + 1)))
    if draw(st.integers(0, 3)) == 0:
        host = draw(st.sampled_from(blips))
        voters = draw(st.lists(st.sampled_from(authors), unique=True))
        columns: dict[str, list[str]] = {"yes": [], "no": [], "maybe": []}
        for voter in voters:
            columns[draw(st.sampled_from(sorted(columns)))].append(voter)
        host.gadget = columns
    # Within two weeks of the theme's date, so a dataset reads as its era.
    return WaveSpec(f"{DOMAIN}!w+{prefix}{index}", creator, title, participants, blips,
                    draw(st.integers(0, 60 * 24 * 14)), theme.start)


@st.composite
def worlds(draw: st.DrawFn, max_users: int = 8, max_waves: int = 6, edgy: bool = False,
           prefix: str = "s") -> World:
    names = draw(st.lists(st.sampled_from(NAMES), min_size=2, max_size=max_users, unique=True))
    users = [f"{name}@{DOMAIN}" for name in names]
    waves = [draw(wave_specs(i, users, edgy, prefix)) for i in range(draw(st.integers(1, max_waves)))]
    states = []
    for wave in waves:
        for user in users:
            if (user not in wave.participants and PUBLIC not in wave.participants) or not draw(st.booleans()):
                continue
            states.append(StateSpec(
                user=user, wave_id=wave.wave_id,
                folder=draw(st.one_of(st.none(), st.sampled_from(["work", "later", "proj-x"]))),
                archived=draw(st.booleans()), muted=draw(st.integers(0, 5)) == 0,
                spam=draw(st.integers(0, 8)) == 0, trashed=draw(st.integers(0, 8)) == 0,
                read_after_blips=draw(st.one_of(st.none(), st.integers(1, len(wave.blips)))),
                tags=draw(st.lists(st.sampled_from(["urgent", "help", "idea", "todo"]), unique=True, max_size=2)),
            ))
    return World(users, waves, states)


def known_users(world: World) -> list[str]:
    """Users the server can authenticate: identity is derived from wave data
    (creators, participants, authors), so a user in no wave cannot log in."""
    seen = {a for w in world.waves for a in [*w.participants, *(b.author for b in w.blips)]}
    return [u for u in world.users if u in seen]


# ---------------------------------------------------------------- writer

def blip_time(wave: WaveSpec, blip: BlipSpec) -> datetime:
    return wave.era_start + timedelta(minutes=wave.start_minutes + blip.minutes)


def write_world(session: Any, world: World) -> None:
    """Insert WORLD using the server's models (imported here so the
    strategies stay importable without a database)."""
    from wave_client_server.user_api import UserWaveState
    from wave_client_server.wave_server import Wave, Wavelet

    for wave in world.waves:
        session.add(Wave(wave_id=wave.wave_id, creator=wave.creator,
                         created_at=blip_time(wave, wave.blips[0])))
        last = max(blip_time(wave, b) for b in wave.blips)
        for blip in wave.blips:
            content: list[Any] = []
            for number, line in enumerate(blip.lines):
                if number:
                    content.append({"type": "line"})
                content.append(line)
            docs: dict[str, Any] = {"main": {"content": content}}
            if blip.gadget is not None:
                content += [{"type": "line"}, {"type": "gadget", "attributes": {"id": "poll", "kind": "yesnomaybe"}}]
                docs["gadgets"] = {"poll": blip.gadget}
            is_root = blip.parent is None
            if is_root:
                docs["digest"] = {"content": [wave.title]}
            else:
                docs["thread"] = {"parent": blip.parent}
            session.add(Wavelet(
                wave_id=wave.wave_id,
                wavelet_id=f"{DOMAIN}!conv+root" if is_root else f"{DOMAIN}!{blip.blip_id}",
                creator=blip.author, creation_time=blip_time(wave, blip),
                last_modified_time=last if is_root else blip_time(wave, blip), version=1, history_hash="",
                participants=wave.participants if is_root else [blip.author], docs=docs,
            ))
    waves_by_id = {w.wave_id: w for w in world.waves}
    for state in world.states:
        wave = waves_by_id[state.wave_id]
        read_at = None
        if state.read_after_blips:
            ordered = sorted(wave.blips, key=lambda b: b.minutes)
            read_at = blip_time(wave, ordered[state.read_after_blips - 1]) + timedelta(seconds=30)
        session.add(UserWaveState(user=state.user, wave_id=state.wave_id, folder=state.folder,
                                  archived=state.archived, muted=state.muted, spam=state.spam,
                                  trashed=state.trashed, read_at=read_at, tags=state.tags))
    session.commit()


# ---------------------------------------------------------------- UI coverage

def thread_depth(wave: WaveSpec) -> int:
    parents = {b.blip_id: b.parent for b in wave.blips}

    def depth(blip_id: str | None) -> int:
        return 0 if blip_id is None else 1 + depth(parents[blip_id])
    return max(depth(b.blip_id) for b in wave.blips)


def _unread_somewhere(world: World) -> bool:
    by_id = {w.wave_id: w for w in world.waves}
    for state in world.states:
        wave = by_id[state.wave_id]
        if state.read_after_blips and state.read_after_blips < len(wave.blips):
            if any(b.author != state.user for b in sorted(wave.blips, key=lambda b: b.minutes)[state.read_after_blips:]):
                return True
    return any(len(w.blips) > 1 for w in world.waves)


# Each feature is a client state the Emacs UI (and web views) must render.
UI_FEATURES: dict[str, Callable[[World], bool]] = {
    "unread wave": _unread_somewhere,
    "fully read wave": lambda w: any(s.read_after_blips == len(next(x for x in w.waves if x.wave_id == s.wave_id).blips) for s in w.states),
    "muted wave": lambda w: any(s.muted for s in w.states),
    "archived wave": lambda w: any(s.archived and not (s.spam or s.trashed) for s in w.states),
    "custom folder": lambda w: any(s.folder for s in w.states),
    "tagged wave": lambda w: any(s.tags for s in w.states),
    "spam": lambda w: any(s.spam for s in w.states),
    "trash": lambda w: any(s.trashed for s in w.states),
    "public wave": lambda w: any(PUBLIC in x.participants for x in w.waves),
    "gadget, all columns voted": lambda w: any(b.gadget and all(b.gadget.values()) for x in w.waves for b in x.blips),
    # Root replies render beside the root, so a chain of 4 blips (root and
    # three nested replies) is what produces two visible indent levels.
    "reply nested 2 deep": lambda w: any(thread_depth(x) >= 4 for x in w.waves),
    "single-blip wave": lambda w: any(len(x.blips) == 1 for x in w.waves),
    ">= 6 participants": lambda w: any(len(x.participants) >= 6 for x in w.waves),
    "title >= 60 chars": lambda w: any(len(x.title) >= 60 for x in w.waves),
    "multi-line blip": lambda w: any(len(b.lines) >= 3 for x in w.waves for b in x.blips),
}


@st.composite
def world_batches(draw: st.DrawFn, max_worlds: int = 40, edgy: bool = False) -> list[World]:
    """Several worlds with distinct id prefixes, mergeable into one database."""
    count = draw(st.integers(1, max_worlds))
    return [draw(worlds(edgy=edgy, prefix=f"g{number}x")) for number in range(count)]


def merge(parts: list[World]) -> World:
    """Union of worlds drawn with distinct prefixes (ids cannot collide)."""
    users: list[str] = []
    for part in parts:
        users += [u for u in part.users if u not in users]
    return World(users, [w for p in parts for w in p.waves], [s for p in parts for s in p.states])


def coverage(world: World) -> dict[str, bool]:
    return {name: check(world) for name, check in UI_FEATURES.items()}
