"""Tests for FedOne delta synthesis (src/wave_client_server/fedone.py)."""

import json
from types import SimpleNamespace

from wave_client_server import fedone


def wavelet(wave_id, wavelet_id, creator, participants, docs):
    return SimpleNamespace(wave_id=wave_id, wavelet_id=wavelet_id, creator=creator,
                           participants=participants, docs=docs)


SEED = [
    wavelet("indexwave!indexwave", "indexwave!indexwave", "system@localhost",
            ["system@localhost"], {"main": {"content": ["Wave Server Index"]}}),
    wavelet("localhost!w+abc", "localhost!conv+root", "alice@localhost",
            ["alice@localhost", "bob@localhost"],
            {"main": {"content": ["Hello", {"type": "line"}, "Bob: hi"]},
             "digest": {"content": ["Greetings"]}}),
    wavelet("localhost!w+abc", "localhost!b+reply1", "charlie@localhost",
            ["charlie@localhost"], {"main": {"content": ["Charlie: late"]}}),
]


def payload(update):
    assert update["messageType"] == "ProtocolWaveletUpdate"
    return json.loads(update["messageJson"])


def test_every_update_has_deltas_and_chained_versions():
    # The client asserts deltas is non-empty and applies a delta only when its
    # pre-version equals the running version.
    for wave_id in ("indexwave!indexwave", "localhost!w+abc"):
        for update in fedone.updates_for_open_request(wave_id, SEED, 7):
            body = payload(update)
            assert update["sequenceNumber"] == 7
            assert body["2"], "client asserts at least one delta"
            version = 0
            for delta in body["2"]:
                assert delta["1"]["1"] == version
                version += len(delta["3"])
            assert body["4"]["1"] == version


def test_index_wave_lists_each_wave_once_with_digest():
    updates = fedone.updates_for_open_request("indexwave!indexwave", SEED, 1)
    assert [payload(u)["1"] for u in updates] == [
        "wave://localhost/indexwave!indexwave/w+abc"]
    operations = payload(updates[0])["2"][0]["3"]
    assert {"3": {"1": "digest", "2": {"1": [{"2": "Greetings"}]}}} in operations


def test_conversation_folds_replies_into_manifest():
    (update,) = fedone.updates_for_open_request("localhost!w+abc", SEED, 1)
    body = payload(update)
    assert body["1"] == "wave://localhost/localhost!w+abc/conv+root"
    first_ops = body["2"][0]["3"]
    assert [op["1"] for op in first_ops if "1" in op] == [
        "alice@localhost", "bob@localhost", "charlie@localhost"]
    manifest = next(op["3"]["2"]["1"] for op in first_ops if "3" in op)
    blip_ids = [c["3"]["2"][0]["2"] for c in manifest
                if "3" in c and c["3"]["1"] == "blip"]
    assert blip_ids == ["b+root", "b+reply1"]
    assert [d["2"] for d in body["2"][1:]] == ["alice@localhost", "charlie@localhost"]


def test_blip_is_balanced_body_with_leading_line():
    components = fedone.blip_components(["text", {"type": "line"}, "more"])
    depth = 0
    for component in components:
        depth += 1 if "3" in component else -1 if "4" in component else 0
        assert depth >= 0
    assert depth == 0
    assert components[1] == {"3": {"1": "line"}}


def test_unknown_wave_yields_no_updates():
    assert fedone.updates_for_open_request("localhost!w+none", SEED, 1) == []
