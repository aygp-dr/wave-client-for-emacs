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


# ---------------------------------------------------------------- oracle
# An independent model of the API's per-user semantics, computed from the
# World spec alone (never from user_api code). Disagreement is a bug in one
# of them; mutation testing showed folder/search logic needed this.

def oracle_wave(world, wave, user):
    state = next((s for s in world.states if s.user == user and s.wave_id == wave.wave_id), None)
    ordered = sorted(wave.blips, key=lambda b: b.minutes)
    addresses = []
    for address in [wave.creator, *wave.participants, *(b.author for b in ordered[1:])]:
        if address not in addresses:
            addresses.append(address)
    read_at_index = state.read_after_blips if state and state.read_after_blips else None
    unread = sum(1 for index, b in enumerate(ordered, 1)
                 if b.author != user and (read_at_index is None or index > read_at_index))
    root = ordered[0]
    return {
        "state": state,
        "participants": addresses,
        "visible": user in addresses or synthetic.PUBLIC in addresses,
        "member": user in addresses,
        "title": wave.title,
        "snippet": " ".join(line for line in root.lines if line != wave.title)[:160],
        "unread_count": unread,
        "blip_count": len(wave.blips),
        "public": synthetic.PUBLIC in addresses,
        "tags": list(state.tags) if state else [],
        "folder": state.folder if state else None,
        "muted": bool(state and state.muted),
        "archived": bool(state and state.archived),
        "read": bool(state and state.read_after_blips),
    }


def oracle_folder(model, wave, user, folder):
    state = model["state"]
    spam, trashed = bool(state and state.spam), bool(state and state.trashed)
    if folder == "spam":
        return spam
    if folder == "trash":
        return trashed
    if spam or trashed:
        return False
    return {
        "inbox": model["member"] and not model["archived"] and model["folder"] is None,
        "active": False,  # generated worlds are older than the 7-day window
        "all": True,
        "by-me": wave.creator == user,
        "history": model["read"],
    }.get(folder, model["folder"] == folder)


def oracle_matches(model, wave, query):
    for token in query.split():
        key, _, value = token.partition(":")
        value = value.lower()
        names = [a.split("@")[0] for a in model["participants"]]
        if key == "is" and value in ("unread", "read", "muted", "public"):
            ok = {"unread": model["unread_count"] > 0, "read": model["unread_count"] == 0,
                  "muted": model["muted"], "public": model["public"]}[value]
        elif key == "with" and value:
            ok = value in names or value in model["participants"]
        elif key == "by" and value:
            ok = value in (wave.creator, wave.creator.split("@")[0])
        elif key == "tag" and value:
            ok = value in [t.lower() for t in model["tags"]]
        else:
            ok = token.lower() in f"{model['title']} {model['snippet']}".lower()
        if not ok:
            return False
    return True


QUERY_TOKENS = synthetic.st.sampled_from(
    ["is:unread", "is:read", "is:muted", "is:public", "with:alice", "with:bob", "with:erin",
     "by:alice", "by:charlie", "tag:urgent", "tag:help", "tag:todo", "wave", "emacs", "zz-none"])


@SETTINGS
@given(world=synthetic.worlds(edgy=True), data=synthetic.st.data())
def test_api_agrees_with_oracle_on_folders_and_summaries(world, data):
    with world_client(world) as (client, _):
        for user in synthetic.known_users(world):
            models = {w.wave_id: (w, oracle_wave(world, w, user)) for w in world.waves}
            custom = sorted({m["folder"] for _, m in models.values() if m["visible"] and m["folder"]})
            for folder in [*FOLDERS, *custom]:
                rows = client.get("/api/waves", params={"folder": folder}, auth=login(user)).json()
                expected = {wid for wid, (w, m) in models.items() if m["visible"] and oracle_folder(m, w, user, folder)}
                assert {r["id"] for r in rows} == expected, folder
                times = [r["last_modified"] for r in rows]
                assert times == sorted(times, reverse=True)
                for row in rows:
                    wave, model = models[row["id"]]
                    assert row["title"] == model["title"]
                    assert row["snippet"] == model["snippet"]
                    assert row["unread_count"] == model["unread_count"]
                    assert row["blip_count"] == model["blip_count"]
                    assert row["public"] == model["public"]
                    assert row["tags"] == model["tags"]
                    assert row["folder"] == model["folder"]
                    assert row["muted"] == model["muted"]
                    assert row["archived"] == model["archived"]
                    assert row["creator"] == wave.creator
                    assert [p["address"] for p in row["participants"]] == model["participants"]
                    for p in row["participants"]:
                        assert p["name"] == p["address"].split("@")[0]
                        expected_avatar = ("/avatars/public.svg" if p["address"] == synthetic.PUBLIC
                                           else f"/avatars/{p['address']}.svg")
                        assert p["avatar"] == expected_avatar
            counts = {f["name"]: f for f in client.get("/api/folders", auth=login(user)).json()}
            assert list(counts)[:len(FOLDERS)] == FOLDERS and sorted(list(counts)[len(FOLDERS):]) == custom
            query = " ".join(data.draw(synthetic.st.lists(QUERY_TOKENS, min_size=1, max_size=2)))
            found = client.get("/api/waves", params={"folder": "all", "q": query}, auth=login(user)).json()
            expected = {wid for wid, (w, m) in models.items()
                        if m["visible"] and oracle_folder(m, w, user, "all") and oracle_matches(m, w, query)}
            assert {r["id"] for r in found} == expected, query


@SETTINGS
@given(synthetic.worlds())
def test_view_gadgets_and_blips_match_world(world):
    with world_client(world) as (client, _):
        for wave in world.waves:
            view = client.get(f"/api/waves/{wave.wave_id}/view", auth=login(wave.creator)).json()
            blips = {b["id"]: b for b in flatten(view["blips"])}
            for spec in wave.blips:
                blip = blips[spec.blip_id]
                assert blip["author"] == spec.author
                assert blip["lines"] == spec.lines
                if spec.gadget is None:
                    assert blip["gadgets"] == []
                else:
                    assert blip["gadgets"] == [{"id": "poll", "kind": "yesnomaybe", "title": "",
                                                "votes": spec.gadget}]
            steps = client.get(f"/api/waves/{wave.wave_id}/history", auth=login(wave.creator)).json()
            ordered = sorted(wave.blips, key=lambda b: b.minutes)
            assert [s["step"] for s in steps] == list(range(1, len(ordered) + 1))
            assert [(s["blip_id"], s["author"], s["text"]) for s in steps] == [
                (b.blip_id, b.author, " / ".join(b.lines)) for b in ordered]


@SETTINGS
@given(synthetic.worlds(edgy=True))
def test_fedone_updates_carry_authors_participants_and_digests(world):
    with world_client(world) as (_, session):
        wavelets = session.query(Wavelet).all()
        index = fedone.updates_for_open_request(fedone.INDEX_WAVE_ID, wavelets, 3)
        assert len(index) == len(world.waves)
        by_url = {json.loads(u["messageJson"])["1"]: json.loads(u["messageJson"]) for u in index}
        for wave in world.waves:
            body = by_url[f"wave://localhost/indexwave!indexwave/{wave.wave_id.split('!')[1]}"]
            (delta,) = body["2"]
            assert delta["2"] == wave.creator
            assert [op["1"] for op in delta["3"] if "1" in op] == wave.participants
            assert {"3": {"1": "digest", "2": {"1": [{"2": wave.title}]}}} in delta["3"]
            assert body["4"] == {"1": len(delta["3"]), "2": ""}

            (update,) = fedone.updates_for_open_request(wave.wave_id, wavelets, 3)
            assert update["messageType"] == "ProtocolWaveletUpdate" and update["version"] == 0
            conv = json.loads(update["messageJson"])
            assert conv["1"] == f"wave://localhost/{wave.wave_id}/conv+root"
            ordered = sorted(wave.blips, key=lambda b: b.minutes)
            expected_participants = []
            for address in [*wave.participants, *(b.author for b in ordered[1:])]:
                if address not in expected_participants:
                    expected_participants.append(address)
            first = conv["2"][0]
            assert first["2"] == wave.creator
            assert [op["1"] for op in first["3"] if "1" in op] == expected_participants
            blip_deltas = conv["2"][1:]
            assert [(d["2"], d["3"][0]["3"]["1"]) for d in blip_deltas] == [
                (b.author, b.blip_id) for b in ordered]
            manifest = next(op["3"]["2"]["1"] for op in first["3"] if "3" in op)
            thread_ids = [c["3"]["2"][0]["2"] for c in manifest if "3" in c and c["3"]["1"] == "thread"]
            parents_with_children = [b.blip_id for b in ordered
                                     if b.blip_id != "b+root" and any(c.parent == b.blip_id for c in wave.blips)]
            assert sorted(thread_ids) == sorted(f"t+{p[2:]}" for p in parents_with_children)
