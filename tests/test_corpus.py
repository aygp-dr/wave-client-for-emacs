"""The static mock corpus (resources/corpus/waves.json) and its loader.

Checks the synthetic.py validity rules, interest exclusivity, UI coverage,
HN provenance (ids, titles, dates, points and tree shape only), and content
hygiene: no PII, no deny-listed words.
"""

import json
import math
import re
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from wave_client_server import corpus, synthetic

DATA = corpus.load()
NAMES = ["alice", "bob", "charlie", "dave", "erin", "frank", "grace", "heidi", "ivan", "judy"]
HN_KEYS = {"hn_id", "title", "created_at", "points", "comments", "top_level_threads", "max_depth", "largest_threads"}

# Kept short and generic on purpose; matched as whole words, case-insensitive.
DENY_WORDS = ["damn", "hell", "crap", "shit", "fuck", "bastard", "bitch", "idiot", "stupid", "moron",
              "retard", "dumb", "sucks", "loser"]
# Real people who come up around these stories; the corpus must not name them.
REAL_NAMES = ["lamport", "kernighan", "ritchie", "thompson", "knuth", "rasmussen", "hickey", "mccarthy",
              "wingo", "torvalds", "stallman"]


def all_text():
    """Every string a user sees: titles, blip lines, folders, tags."""
    for wave in DATA["waves"]:
        yield wave["id"], wave["title"]
        for blip in wave["blips"]:
            for line in blip["lines"]:
                yield f"{wave['id']}/{blip['id']}", line
    for state in DATA["states"]:
        for value in [state.get("folder") or "", *state.get("tags", [])]:
            yield f"state {state['user']} {state['wave']}", value


def test_corpus_is_valid():
    assert corpus.problems(DATA) == []


def test_ten_users_with_two_or_three_interests():
    assert sorted(DATA["users"]) == sorted(f"{n}@localhost" for n in NAMES)
    for user, info in DATA["users"].items():
        assert 2 <= len(info["interests"]) <= 3, user
        assert len(set(info["interests"])) == len(info["interests"]), user


def test_interest_exclusivity():
    for wave in DATA["waves"]:
        actors = {wave["creator"], *wave["participants"], *(b["author"] for b in wave["blips"])}
        actors |= {v for b in wave["blips"] for column in (b.get("gadget") or {}).values() for v in column}
        actors.discard(corpus.PUBLIC)
        for user in actors:
            assert wave["topic"] in DATA["users"][user]["interests"], (wave["id"], user)
    for state in DATA["states"]:
        wave = next(w for w in DATA["waves"] if w["id"] == state["wave"])
        assert wave["topic"] in DATA["users"][state["user"]]["interests"], (state["user"], wave["id"])


def test_topics_overlap_enough_for_a_six_person_wave():
    assert max(len([p for p in w["participants"] if p != corpus.PUBLIC]) for w in DATA["waves"]) >= 6
    assert 6 <= len(DATA["topics"]) - 1 <= 8, "6-8 research clusters plus the Wave-era topic"
    assert "google-wave" in DATA["topics"]


def test_every_ui_feature_is_covered():
    coverage = synthetic.coverage(corpus.to_world(DATA))
    assert [name for name, ok in coverage.items() if not ok] == []


def test_validator_catches_broken_corpora():
    """The rules are not vacuous: each mutation below is reported."""
    def broken(mutate):
        data = json.loads(json.dumps(DATA))
        mutate(data)
        return corpus.problems(data)

    def outsider_reply(d):
        wave = next(w for w in d["waves"] if w["topic"] == "agent-sandboxing")
        wave["participants"].append("alice@localhost")
        wave["blips"][-1]["author"] = "alice@localhost"
    assert broken(outsider_reply)
    assert broken(lambda d: d["waves"][0]["blips"][1].update(parent="b+nope"))
    assert broken(lambda d: d["waves"][0]["blips"][1].update(at="2001-01-01T00:00:00"))
    assert broken(lambda d: d["states"].append({"user": "judy@localhost", "wave": d["waves"][2]["id"]}))


def test_hn_snapshot_holds_only_metadata_and_shape():
    snapshot = DATA["hn_snapshot"]
    for story in snapshot.values():
        assert set(story) == HN_KEYS, "no comment text, authors or children in the snapshot"
    used = {str(w["source"]["hn_id"]) for w in DATA["waves"] if "source" in w}
    assert used == set(snapshot)
    titles = {s["title"] for s in snapshot.values()}
    for where, text in all_text():
        assert text not in titles or where.count("/") == 0, f"{where}: a blip repeats a story title"


def test_hn_waves_follow_story_shape_and_dates():
    per_topic: dict[str, int] = {}
    for wave in DATA["waves"]:
        if "source" not in wave:
            continue
        story = DATA["hn_snapshot"][str(wave["source"]["hn_id"])]
        per_topic[wave["topic"]] = per_topic.get(wave["topic"], 0) + 1
        assert wave["title"] == story["title"]
        assert wave["source"]["url"] == f"https://news.ycombinator.com/item?id={story['hn_id']}"
        want = min(15, max(4, 2 + int(math.sqrt(story["comments"]) / 2 + 0.5)))
        assert len(wave["blips"]) == want, wave["id"]
        reply_depth = synthetic.thread_depth(next(w for w in corpus.to_world(DATA).waves if w.wave_id == wave["id"])) - 1
        assert reply_depth <= story["max_depth"], wave["id"]
        assert corpus.parse_time(wave["created"]) > datetime.fromisoformat(story["created_at"][:19])
    assert all(3 <= count <= 5 for count in per_topic.values()), per_topic
    for wave in DATA["waves"]:
        if wave["topic"] == "google-wave":
            assert wave["created"][:4] in ("2009", "2010"), wave["id"]
        assert 1 <= len(wave["blips"]) <= 15


def test_no_pii():
    raw = json.dumps({k: DATA[k] for k in ("users", "waves", "states", "hn_snapshot")}).lower()
    addresses = set(re.findall(r"[\w.+-]+@[\w.-]+", raw))
    assert addresses <= {f"{n}@localhost" for n in NAMES} | {corpus.PUBLIC}
    assert "/users/" not in raw and "/home/" not in raw
    hosts = set(re.findall(r"\b(?:[a-z0-9-]+\.)+(?:com|org|net|io|edu|dev|sh|local)\b", raw))
    assert hosts <= {"news.ycombinator.com"}, sorted(hosts)
    for name in REAL_NAMES:
        assert not re.search(rf"\b{name}\b", raw), "a real person is named in the corpus"


def test_no_deny_listed_words():
    pattern = re.compile(r"\b(?:" + "|".join(DENY_WORDS) + r")\b", re.IGNORECASE)
    hits = [where for where, text in all_text() if pattern.search(text)]
    titles = [s["title"] for s in DATA["hn_snapshot"].values() if pattern.search(s["title"])]
    assert not hits and not titles, f"{len(hits) + len(titles)} place(s) use a deny-listed word: {hits}"


@pytest.fixture
def corpus_client(tmp_path):
    from wave_client_server.wave_server import Base, app, get_db

    engine = create_engine(f"sqlite:///{tmp_path / 'corpus.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    corpus.write(session, DATA)
    session.close()

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()


def test_loaded_corpus_serves_per_user_views(corpus_client):
    for name in NAMES:
        rows = corpus_client.get("/api/waves", params={"folder": "all"}, auth=(name, name)).json()
        topics = DATA["users"][f"{name}@localhost"]["interests"]
        visible = {w["id"] for w in DATA["waves"]
                   if f"{name}@localhost" in w["participants"] or corpus.PUBLIC in w["participants"]}
        assert rows, name
        assert {r["id"] for r in rows} <= visible, name
        assert all(next(w for w in DATA["waves"] if w["id"] == r["id"])["topic"] in topics
                   or corpus.PUBLIC in r["participants"] or r["public"] for r in rows), name
    view = corpus_client.get("/api/waves/localhost!w+corpus-gw5/view", auth=("alice", "alice")).json()
    assert len(view["participants"]) == 6
