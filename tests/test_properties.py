"""Properties of the per-user API and FedOne synthesis over generated worlds.

Each example gets a fresh in-memory database via FastAPI's dependency
override, so properties never touch the development database.
"""

import json
from contextlib import contextmanager

from fastapi.testclient import TestClient
from hypothesis import HealthCheck, given, settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from wave_client_server import fedone, synthetic
from wave_client_server.user_api import FOLDERS
from wave_client_server.wave_server import Base, Wavelet, app, get_db

# Example count comes from the Hypothesis profile (tests/conftest.py):
# "default" 60, "mutation" 8 (HYPOTHESIS_PROFILE=mutation).
SETTINGS = settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])


@contextmanager
def world_client(world):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    synthetic.write_world(session, world)

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    try:
        yield TestClient(app), session
    finally:
        app.dependency_overrides.pop(get_db, None)
        session.close()
        engine.dispose()


def login(user):
    name = user.split("@")[0]
    return (name, name)


def flatten(blips):
    for blip in blips:
        yield blip
        yield from flatten(blip["children"])


def tree_ids(blips, parent=None, out=None):
    out = {} if out is None else out
    for blip in blips:
        out[blip["id"]] = parent
        tree_ids(blip["children"], blip["id"], out)
    return out


@SETTINGS
@given(synthetic.worlds(edgy=True))
def test_folder_counts_match_listings_and_spam_trash_exclusive(world):
    with world_client(world) as (client, _):
        for user in synthetic.known_users(world):
            counts = {f["name"]: f for f in client.get("/api/folders", auth=login(user)).json()}
            listed = {}
            for name in counts:
                rows = client.get("/api/waves", params={"folder": name}, auth=login(user)).json()
                listed[name] = {r["id"] for r in rows}
                assert counts[name]["total"] == len(rows)
                assert counts[name]["unread"] == sum(1 for r in rows if r["unread_count"])
            elsewhere = set().union(*(listed[n] for n in FOLDERS if n not in ("spam", "trash")))
            assert not (listed["spam"] | listed["trash"]) & elsewhere
            assert listed["inbox"] <= listed["all"]


@SETTINGS
@given(synthetic.worlds(edgy=True))
def test_visibility_is_participation_or_public(world):
    with world_client(world) as (client, _):
        for user in synthetic.known_users(world):
            seen = {r["id"] for r in client.get("/api/waves", params={"folder": "all"}, auth=login(user)).json()}
            spam_or_trash = {s.wave_id for s in world.states if s.user == user and (s.spam or s.trashed)}
            expected = {w.wave_id for w in world.waves
                        if user in w.participants or synthetic.PUBLIC in w.participants
                        or any(b.author == user for b in w.blips)}
            assert seen == expected - spam_or_trash


@SETTINGS
@given(synthetic.worlds(edgy=True))
def test_view_tree_is_the_thread_structure(world):
    with world_client(world) as (client, _):
        for wave in world.waves:
            user = wave.creator
            view = client.get(f"/api/waves/{wave.wave_id}/view", auth=login(user)).json()
            parents = tree_ids(view["blips"])
            assert set(parents) == {b.blip_id for b in wave.blips}
            for blip in wave.blips:
                expected_parent = None if blip.parent in (None, "b+root") and blip.blip_id == "b+root" else blip.parent
                assert parents[blip.blip_id] == expected_parent
            unread_flags = [blip["unread"] for blip in flatten(view["blips"])]
            assert view["unread_count"] == sum(unread_flags) <= view["blip_count"] == len(wave.blips)


@SETTINGS
@given(synthetic.worlds(edgy=True))
def test_read_zeroes_unread_and_is_idempotent(world):
    with world_client(world) as (client, _):
        wave = world.waves[0]
        user = wave.creator
        first = client.post(f"/api/waves/{wave.wave_id}/read", auth=login(user)).json()
        second = client.post(f"/api/waves/{wave.wave_id}/read", auth=login(user)).json()
        assert first["unread_count"] == second["unread_count"] == 0


@SETTINGS
@given(synthetic.worlds(edgy=True))
def test_fedone_manifest_mirrors_view_tree(world):
    with world_client(world) as (client, session):
        for wave in world.waves:
            wavelets = session.query(Wavelet).filter_by(wave_id=wave.wave_id).all()
            (update,) = fedone.updates_for_open_request(wave.wave_id, wavelets, 1)
            body = json.loads(update["messageJson"])
            version = 0
            for delta in body["2"]:
                assert delta["1"]["1"] == version
                version += len(delta["3"])
            manifest = next(op["3"]["2"]["1"] for op in body["2"][0]["3"]
                            if "3" in op and op["3"]["1"] == "conversation")
            stack, manifest_parent, depth = [], {}, 0
            for component in manifest:
                if "3" in component:
                    depth += 1
                    element = component["3"]
                    if element["1"] == "blip":
                        blip_id = element["2"][0]["2"]
                        enclosing = [b for kind, b in stack if kind == "blip"]
                        manifest_parent[blip_id] = enclosing[-1] if enclosing else None
                        stack.append(("blip", blip_id))
                    else:
                        stack.append((element["1"], None))
                elif "4" in component:
                    depth -= 1
                    stack.pop()
                assert depth >= 0
            assert depth == 0
            view = client.get(f"/api/waves/{wave.wave_id}/view", auth=login(wave.creator)).json()
            tree = tree_ids(view["blips"])
            # top-level replies to the root sit beside it in the manifest
            normalized = {b: (None if p == "b+root" else p) for b, p in tree.items()}
            assert manifest_parent == normalized
            docs = {op["3"]["1"] for d in body["2"] for op in d["3"] if "3" in op}
            assert docs == {"conversation"} | {b.blip_id for b in wave.blips}


@SETTINGS
@given(world=synthetic.worlds(), st_choice=synthetic.st.sampled_from(["yes", "no", "maybe"]))
def test_vote_puts_voter_in_exactly_one_column(world, st_choice):
    with world_client(world) as (client, _):
        polls = [(w, b) for w in world.waves for b in w.blips if b.gadget is not None]
        for wave, _blip in polls:
            voter = wave.creator
            (gadget,) = [g for g in client.post(f"/api/waves/{wave.wave_id}/gadgets/poll/vote",
                                                json={"choice": st_choice}, auth=login(voter)).json()]
            columns = [choice for choice, voters in gadget["votes"].items() if voter in voters]
            assert columns == [st_choice]
