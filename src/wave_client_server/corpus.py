"""The static mock corpus (resources/corpus/waves.json): load it, check it,
and turn it into a synthetic.World so write_world() can put it in a database.

Unlike synthetic.py, nothing here is generated: the corpus is hand-written,
checked in, and loads offline. The validity rules are synthetic.py's, plus
interest exclusivity (a user only creates, joins, replies to or votes on
waves whose topic they hold).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

CORPUS_PATH = Path(__file__).resolve().parents[2] / "resources" / "corpus" / "waves.json"
PUBLIC = "public@localhost"
TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"


def load(path: Path | str = CORPUS_PATH) -> dict[str, Any]:
    return json.loads(Path(path).read_text())


def parse_time(text: str) -> datetime:
    return datetime.strptime(text, TIME_FORMAT)


def problems(corpus: dict[str, Any]) -> list[str]:
    """Every rule the corpus breaks, as readable strings (empty = valid)."""
    found: list[str] = []
    users = corpus["users"]
    topics = corpus["topics"]
    wave_ids = set()
    blip_counts: dict[str, list[dict[str, Any]]] = {}
    for user, info in users.items():
        for topic in info["interests"]:
            if topic not in topics:
                found.append(f"{user}: unknown topic {topic}")
    for wave in corpus["waves"]:
        wid = wave["id"]
        if wid in wave_ids:
            found.append(f"{wid}: duplicate id")
        wave_ids.add(wid)
        topic = wave["topic"]
        people = [p for p in wave["participants"] if p != PUBLIC]
        if wave["creator"] not in people:
            found.append(f"{wid}: creator is not a participant")
        for person in people:
            if person not in users:
                found.append(f"{wid}: {person} is not a corpus user")
            elif topic not in users[person]["interests"]:
                found.append(f"{wid}: {person} does not hold topic {topic}")
        seen: dict[str, datetime] = {}
        previous: datetime | None = None
        blips = wave["blips"]
        blip_counts[wid] = blips
        if not blips or blips[0]["parent"] is not None or blips[0]["id"] != "b+root":
            found.append(f"{wid}: first blip must be b+root with no parent")
        if blips and blips[0]["author"] != wave["creator"]:
            found.append(f"{wid}: root blip not by the creator")
        for blip in blips:
            at = parse_time(blip["at"])
            if previous is not None and at <= previous:
                found.append(f"{wid}/{blip['id']}: time does not increase")
            previous = at
            if blip["author"] not in people:
                found.append(f"{wid}/{blip['id']}: author not a participant")
            if blip is not blips[0] and blip["parent"] not in seen:
                found.append(f"{wid}/{blip['id']}: parent is not an earlier blip of this wave")
            if blip["id"] in seen:
                found.append(f"{wid}/{blip['id']}: duplicate blip id")
            if not blip["lines"] or not all(isinstance(line, str) and line.strip() for line in blip["lines"]):
                found.append(f"{wid}/{blip['id']}: empty line")
            gadget = blip.get("gadget")
            if gadget is not None:
                if sorted(gadget) != ["maybe", "no", "yes"]:
                    found.append(f"{wid}/{blip['id']}: gadget columns must be yes/no/maybe")
                voters = [v for column in gadget.values() for v in column]
                if len(voters) != len(set(voters)):
                    found.append(f"{wid}/{blip['id']}: a voter is in more than one column")
                if any(v not in people for v in voters):
                    found.append(f"{wid}/{blip['id']}: voter not a participant")
            seen[blip["id"]] = at
        if blips and wave["created"] != blips[0]["at"]:
            found.append(f"{wid}: created differs from the root blip time")
    pairs = set()
    for state in corpus["states"]:
        key = (state["user"], state["wave"])
        if key in pairs:
            found.append(f"state {key}: duplicate")
        pairs.add(key)
        wave = next((w for w in corpus["waves"] if w["id"] == state["wave"]), None)
        if wave is None:
            found.append(f"state {key}: unknown wave")
            continue
        if state["user"] not in wave["participants"] and PUBLIC not in wave["participants"]:
            found.append(f"state {key}: user cannot see the wave")
        read = state.get("read_through")
        if read is not None and read not in {b["id"] for b in wave["blips"]}:
            found.append(f"state {key}: read_through names no blip of the wave")
    return found


def to_world(corpus: dict[str, Any]) -> Any:
    """The corpus as a synthetic.World (times become minute offsets from
    synthetic.BASE_TIME; negative for 2009-2010 waves, which is fine)."""
    from wave_client_server import synthetic

    waves = []
    for wave in corpus["waves"]:
        start = parse_time(wave["created"])
        blips = []
        for blip in wave["blips"]:
            minutes = int((parse_time(blip["at"]) - start).total_seconds() // 60)
            lines = list(blip["lines"])
            if blip["parent"] is None:
                lines = [wave["title"], *lines]   # write_world's convention: root starts with the title
            blips.append(synthetic.BlipSpec(blip["id"], blip["author"], blip["parent"], lines, minutes,
                                            blip.get("gadget")))
        start_minutes = int((start - synthetic.BASE_TIME).total_seconds() // 60)
        waves.append(synthetic.WaveSpec(wave["id"], wave["creator"], wave["title"], wave["participants"],
                                        blips, start_minutes))
    by_id = {w.wave_id: w for w in waves}
    states = []
    for state in corpus["states"]:
        read = state.get("read_through")
        read_after = None
        if read is not None:
            ordered = sorted(by_id[state["wave"]].blips, key=lambda b: b.minutes)
            read_after = [b.blip_id for b in ordered].index(read) + 1
        states.append(synthetic.StateSpec(
            user=state["user"], wave_id=state["wave"], folder=state.get("folder"),
            archived=state.get("archived", False), muted=state.get("muted", False),
            spam=state.get("spam", False), trashed=state.get("trashed", False),
            read_after_blips=read_after, tags=list(state.get("tags", []))))
    return synthetic.World(list(corpus["users"]), waves, states)


def write(session: Any, corpus: dict[str, Any]) -> None:
    """write_world(), then stamp topic and HN provenance on each root wavelet
    (docs.topic, docs.source) so they are visible through the admin API."""
    from wave_client_server import synthetic
    from wave_client_server.wave_server import Wavelet

    synthetic.write_world(session, to_world(corpus))
    for wave in corpus["waves"]:
        root = session.query(Wavelet).filter_by(wave_id=wave["id"], wavelet_id="localhost!conv+root").one()
        docs = dict(root.docs)
        docs["topic"] = wave["topic"]
        if "source" in wave:
            docs["source"] = wave["source"]
        root.docs = docs
    session.commit()
