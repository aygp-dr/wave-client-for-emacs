"""Per-user and admin API (src/wave_client_server/user_api.py).

Each test inserts its own uniquely named users and wave, and removes them,
so it neither depends on nor disturbs the seeded development database.
"""

import uuid
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from wave_client_server.user_api import UserWaveState
from wave_client_server.wave_server import SessionLocal, Wave, Wavelet, app

client = TestClient(app)


@pytest.fixture
def scenario():
    tag = uuid.uuid4().hex[:6]
    owner, friend, outsider = (f"{name}{tag}@localhost" for name in ("own", "fri", "out"))
    wave_id = f"localhost!w+t{tag}"
    other_wave = f"localhost!w+u{tag}"
    earlier = datetime.utcnow() - timedelta(hours=2)
    db = SessionLocal()
    db.add(Wave(wave_id=wave_id, creator=owner))
    db.add(Wave(wave_id=other_wave, creator=outsider))
    db.add(Wavelet(wave_id=wave_id, wavelet_id="localhost!conv+root", creator=owner,
                   creation_time=earlier, last_modified_time=earlier, version=1,
                   participants=[owner, friend],
                   docs={"main": {"content": [f"Topic {tag}", {"type": "line"}, "body text"]},
                         "digest": {"content": [f"Topic {tag}"]}}))
    db.add(Wavelet(wave_id=wave_id, wavelet_id="localhost!b+r1", creator=friend,
                   creation_time=earlier + timedelta(minutes=5), version=1, participants=[friend],
                   docs={"main": {"content": ["first reply"]}, "thread": {"parent": "b+root"}}))
    db.add(Wavelet(wave_id=wave_id, wavelet_id="localhost!b+poll", creator=owner,
                   creation_time=earlier + timedelta(minutes=6), version=1, participants=[owner],
                   docs={"main": {"content": [{"type": "gadget", "attributes": {"id": "g1"}}]},
                         "thread": {"parent": "b+root"}}))
    db.add(Wavelet(wave_id=other_wave, wavelet_id="localhost!conv+root", creator=outsider,
                   creation_time=earlier, version=1, participants=[outsider],
                   docs={"main": {"content": ["private"]}}))
    db.commit()
    db.close()
    yield {"tag": tag, "owner": owner, "friend": friend, "outsider": outsider,
           "wave": wave_id, "other": other_wave}
    db = SessionLocal()
    for wid in (wave_id, other_wave):
        db.query(Wavelet).filter_by(wave_id=wid).delete()
        db.query(Wave).filter_by(wave_id=wid).delete()
        db.query(UserWaveState).filter_by(wave_id=wid).delete()
    db.commit()
    db.close()


def auth(address):
    local = address.split("@")[0]
    return (local, local)


def summary(user, wave_id, folder="all"):
    rows = client.get("/api/waves", params={"folder": folder}, auth=auth(user)).json()
    return next((row for row in rows if row["id"] == wave_id), None)


def test_basic_auth_required_and_checked(scenario):
    response = client.get("/api/me")
    assert response.status_code == 401
    assert response.headers["www-authenticate"].startswith("Basic")
    assert client.get("/api/me", auth=(scenario["owner"], "wrong")).status_code == 401
    me = client.get("/api/me", auth=auth(scenario["owner"])).json()
    assert me["address"] == scenario["owner"]
    assert me["avatar"].startswith("/avatars/")


def test_admin_requires_admin_credentials(scenario):
    assert client.get("/api/admin/stats").status_code == 401
    assert client.get("/api/admin/stats", auth=auth(scenario["owner"])).status_code == 401
    stats = client.get("/api/admin/stats", auth=("admin", "admin")).json()
    assert stats["waves"] >= 2


def test_waves_are_private_to_participants(scenario):
    assert summary(scenario["owner"], scenario["other"]) is None
    assert client.get(f"/api/waves/{scenario['other']}/view", auth=auth(scenario["owner"])).status_code == 404


def test_read_and_unread_round_trip(scenario):
    owner, wave = scenario["owner"], scenario["wave"]
    assert summary(owner, wave, "inbox")["unread_count"] == 1  # friend's reply
    client.post(f"/api/waves/{wave}/read", auth=auth(owner))
    assert summary(owner, wave, "inbox")["unread_count"] == 0
    client.post(f"/api/waves/{wave}/unread", auth=auth(owner))
    assert summary(owner, wave, "inbox")["unread_count"] == 1


def test_own_reply_stays_read_but_others_reply_is_unread(scenario):
    owner, friend, wave = scenario["owner"], scenario["friend"], scenario["wave"]
    client.post(f"/api/waves/{wave}/read", auth=auth(owner))
    client.post(f"/api/waves/{wave}/blips", json={"text": "mine", "parent": "b+r1"}, auth=auth(owner))
    assert summary(owner, wave)["unread_count"] == 0
    client.post(f"/api/waves/{wave}/blips", json={"text": "theirs"}, auth=auth(friend))
    assert summary(owner, wave)["unread_count"] == 1


def test_reply_nests_under_parent(scenario):
    owner, wave = scenario["owner"], scenario["wave"]
    created = client.post(f"/api/waves/{wave}/blips", json={"text": "nested", "parent": "b+r1"},
                          auth=auth(owner)).json()
    view = client.get(f"/api/waves/{wave}/view", auth=auth(owner)).json()
    (root,) = view["blips"]
    first_reply = next(child for child in root["children"] if child["id"] == "b+r1")
    assert [child["id"] for child in first_reply["children"]] == [created["id"]]
    bad = client.post(f"/api/waves/{wave}/blips", json={"text": "x", "parent": "b+none"}, auth=auth(owner))
    assert bad.status_code == 422


def test_archive_moves_out_of_inbox_and_restore_brings_back(scenario):
    owner, wave = scenario["owner"], scenario["wave"]
    client.post(f"/api/waves/{wave}/archive", auth=auth(owner))
    assert summary(owner, wave, "inbox") is None
    assert summary(owner, wave, "all") is not None
    client.post(f"/api/waves/{wave}/restore", auth=auth(owner))
    assert summary(owner, wave, "inbox") is not None


def test_folders_tags_and_search(scenario):
    owner, wave, tag = scenario["owner"], scenario["wave"], scenario["tag"]
    client.post(f"/api/waves/{wave}/folder", json={"name": f"proj{tag}"}, auth=auth(owner))
    client.post(f"/api/waves/{wave}/tags", json={"add": ["urgent"]}, auth=auth(owner))
    names = [f["name"] for f in client.get("/api/folders", auth=auth(owner)).json()]
    assert f"proj{tag}" in names
    assert summary(owner, wave, f"proj{tag}")["tags"] == ["urgent"]
    found = client.get("/api/waves", params={"folder": "all", "q": f"tag:urgent with:fri{tag}"},
                       auth=auth(owner)).json()
    assert [row["id"] for row in found] == [wave]
    assert client.post(f"/api/waves/{wave}/folder", json={"name": "inbox"}, auth=auth(owner)).status_code == 422


def test_gadget_vote_replaces_previous_choice(scenario):
    owner, wave = scenario["owner"], scenario["wave"]
    client.post(f"/api/waves/{wave}/gadgets/g1/vote", json={"choice": "yes"}, auth=auth(owner))
    (gadget,) = client.post(f"/api/waves/{wave}/gadgets/g1/vote", json={"choice": "no"}, auth=auth(owner)).json()
    assert gadget["votes"] == {"yes": [], "no": [owner], "maybe": []}
    assert client.post(f"/api/waves/{wave}/gadgets/g1/vote", json={"choice": "sure"},
                       auth=auth(owner)).status_code == 422


def test_history_orders_blips_by_creation(scenario):
    steps = client.get(f"/api/waves/{scenario['wave']}/history", auth=auth(scenario["owner"])).json()
    assert [step["blip_id"] for step in steps] == ["b+root", "b+r1", "b+poll"]


def test_new_wave_and_participant(scenario):
    owner, tag = scenario["owner"], scenario["tag"]
    created = client.post("/api/waves", json={"title": f"New {tag}", "text": "hi", "participants": [f"fri{tag}"]},
                          auth=auth(owner))
    assert created.status_code == 201
    new_id = created.json()["id"]
    try:
        client.post(f"/api/waves/{new_id}/participants", json={"address": f"out{tag}"}, auth=auth(owner))
        names = [p["name"] for p in summary(owner, new_id)["participants"]]
        assert names == [f"own{tag}", f"fri{tag}", f"out{tag}"]
        assert summary(scenario["outsider"], new_id) is not None
    finally:
        db = SessionLocal()
        db.query(Wavelet).filter_by(wave_id=new_id).delete()
        db.query(Wave).filter_by(wave_id=new_id).delete()
        db.query(UserWaveState).filter_by(wave_id=new_id).delete()
        db.commit()
        db.close()


def test_change_is_pushed_to_open_websocket_channel(scenario):
    import json as jsonlib
    owner, friend, wave = scenario["owner"], scenario["friend"], scenario["wave"]
    with client.websocket_connect("/socket") as socket:
        socket.send_text(jsonlib.dumps({"version": 0, "sequenceNumber": 7, "messageType": "ProtocolOpenRequest",
                                        "messageJson": jsonlib.dumps({"1": owner, "2": wave})}))
        initial = jsonlib.loads(socket.receive_text())
        assert initial["sequenceNumber"] == 7
        created = client.post(f"/api/waves/{wave}/blips", json={"text": "pushed", "parent": "b+r1"},
                              auth=auth(friend)).json()
        pushed = jsonlib.loads(socket.receive_text())
        assert pushed["sequenceNumber"] == 7
        body = jsonlib.loads(pushed["messageJson"])
        assert body["2"][0]["1"]["1"] == 0, "full resend from version 0 resets the client's wavelet"
        documents = {op["3"]["1"] for delta in body["2"] for op in delta["3"] if "3" in op}
        assert created["id"] in documents
