"""FedOne-style wavelet updates synthesized from stored document snapshots.

The 2010 Emacs client (lisp/wave-client-websocket.el) never reads snapshots:
it rebuilds every wavelet by replaying ProtocolWaveletDelta messages, and
asserts that each ProtocolWaveletUpdate carries at least one delta. The
database stores documents as snapshots ({"content": ["text", {"type": "line"}]}),
so this module turns a snapshot into the deltas that would have produced it.

Wire shapes, matching the client's parser:

  ProtocolWaveletUpdate  {"1": wavelet-url, "2": [delta...], "4": hashed-version}
  ProtocolWaveletDelta   {"1": hashed-version, "2": author, "3": [op...]}
  ProtocolHashedVersion  {"1": version, "2": history-hash}
  WaveletOperation       {"1": address} add participant
                         {"3": {"1": doc-id, "2": {"1": [component...]}}} mutate doc
  DocOp component        {"2": text}  {"3": {"1": type, "2": [{"1": k, "2": v}]}}
                         {"4": true}  (element end)

The client applies a delta only when its pre-version equals the wavelet's
current version, and checks post-version = pre-version + len(ops), so the
deltas in one update are chained.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

INDEX_WAVE_ID = "indexwave!indexwave"
DOMAIN = "localhost"

Component = dict[str, Any]
Operation = dict[str, Any]


def characters(text: str) -> Component:
    return {"2": text}


def element_start(element_type: str, attributes: dict[str, str] | None = None) -> Component:
    element: dict[str, Any] = {"1": element_type}
    if attributes:
        element["2"] = [{"1": key, "2": value} for key, value in attributes.items()]
    return {"3": element}


def element_end() -> Component:
    return {"4": True}


def add_participant(address: str) -> Operation:
    return {"1": address}


def mutate_document(doc_id: str, components: list[Component]) -> Operation:
    return {"3": {"1": doc_id, "2": {"1": components}}}


def snapshot_to_components(content: Iterable[Any]) -> list[Component]:
    """Translate stored snapshot content to element/character components.

    Strings become characters; {"type": t, "attributes": {...}} becomes an
    empty element <t .../>. Content not already starting with a line gets
    one, since the client fills a paragraph each time a line element closes.
    """
    components: list[Component] = []
    items = list(content)
    if not items or not (isinstance(items[0], dict) and items[0].get("type") == "line"):
        components += [element_start("line"), element_end()]
    for item in items:
        if isinstance(item, str):
            if item:
                components.append(characters(item))
        elif isinstance(item, dict) and "type" in item:
            attributes = {key: str(value) for key, value in (item.get("attributes") or {}).items()}
            components += [element_start(item["type"], attributes), element_end()]
    return components


def blip_components(content: Iterable[Any]) -> list[Component]:
    return [element_start("body"), *snapshot_to_components(content), element_end()]


def plain_text(content: Iterable[Any]) -> str:
    return " ".join(item for item in content if isinstance(item, str))


def local_part(qualified_id: str) -> str:
    """'localhost!conv+root' -> 'conv+root'."""
    return qualified_id.split("!", 1)[-1]


def wavelet_url(wave_id: str, wavelet_id: str) -> str:
    return f"wave://{DOMAIN}/{wave_id}/{local_part(wavelet_id)}"


def chain_deltas(authored_ops: list[tuple[str, list[Operation]]]) -> tuple[list[dict], int]:
    """Number deltas consecutively from version 0; return (deltas, final version)."""
    deltas = []
    version = 0
    for author, operations in authored_ops:
        if not operations:
            continue
        deltas.append({"1": {"1": version, "2": ""}, "2": author, "3": operations})
        version += len(operations)
    return deltas, version


def wavelet_update(url: str, authored_ops: list[tuple[str, list[Operation]]],
                   sequence_number: int) -> dict:
    deltas, version = chain_deltas(authored_ops)
    return {
        "version": 0,
        "sequenceNumber": sequence_number,
        "messageType": "ProtocolWaveletUpdate",
        "messageJson": json.dumps({"1": url, "2": deltas, "4": {"1": version, "2": ""}}),
    }


def index_wave_updates(wavelets: list[Any], sequence_number: int) -> list[dict]:
    """One index wavelet per wave, named after the wave, holding its digest.

    The client lists the inbox as the wavelets of indexwave!indexwave and uses
    each wavelet id as the id of the wave to open.
    """
    by_wave: dict[str, list[Any]] = {}
    for wavelet in wavelets:
        if wavelet.wave_id != INDEX_WAVE_ID:
            by_wave.setdefault(wavelet.wave_id, []).append(wavelet)

    updates = []
    for wave_id, wave_wavelets in sorted(by_wave.items()):
        root = next((w for w in wave_wavelets if "conv+root" in w.wavelet_id), wave_wavelets[0])
        docs = root.docs or {}
        digest_doc = docs.get("digest") or docs.get("main") or {}
        digest = plain_text(digest_doc.get("content", []))
        creator = root.creator or f"system@{DOMAIN}"
        url = f"wave://{DOMAIN}/{INDEX_WAVE_ID}/{local_part(wave_id)}"
        updates.append(wavelet_update(
            url,
            [(creator, [*(add_participant(p) for p in (root.participants or [creator])),
                        mutate_document("digest", [characters(digest)])])],
            sequence_number,
        ))
    return updates


def conversation_update(wave_id: str, wavelets: list[Any], sequence_number: int) -> dict | None:
    """Fold a wave's stored wavelets into one conv+root conversation.

    The root wavelet's main doc becomes blip b+root; each other stored wavelet
    (the seed keeps replies as separate b+ wavelets) becomes one more blip,
    authored by its creator so blip contributors come out right.
    """
    if not wavelets:
        return None
    root = next((w for w in wavelets if "conv+root" in w.wavelet_id), wavelets[0])
    replies = [w for w in wavelets if w is not root]

    blips: list[tuple[str, str, list[Any]]] = []  # (blip id, author, content)
    root_docs = root.docs or {}
    root_author = root.creator or f"system@{DOMAIN}"
    blips.append(("b+root", root_author, root_docs.get("main", {}).get("content", [])))
    for reply in replies:
        reply_docs = reply.docs or {}
        blips.append((
            local_part(reply.wavelet_id) if local_part(reply.wavelet_id).startswith("b+")
            else f"b+{local_part(reply.wavelet_id)}",
            reply.creator or root_author,
            reply_docs.get("main", {}).get("content", []),
        ))

    participants: list[str] = list(root.participants or [root_author])
    for reply in replies:
        for participant in reply.participants or []:
            if participant not in participants:
                participants.append(participant)

    manifest = [element_start("conversation")]
    for blip_id, _, _ in blips:
        manifest += [element_start("blip", {"id": blip_id}), element_end()]
    manifest.append(element_end())

    authored_ops: list[tuple[str, list[Operation]]] = [
        (root_author, [*(add_participant(p) for p in participants),
                       mutate_document("conversation", manifest)]),
    ]
    for blip_id, author, content in blips:
        authored_ops.append((author, [mutate_document(blip_id, blip_components(content))]))

    return wavelet_update(wavelet_url(wave_id, f"{DOMAIN}!conv+root"), authored_ops, sequence_number)


def updates_for_open_request(wave_id: str, wavelets: list[Any], sequence_number: int) -> list[dict]:
    """All ProtocolWaveletUpdate messages answering a ProtocolOpenRequest."""
    if wave_id == INDEX_WAVE_ID:
        return index_wave_updates(wavelets, sequence_number)
    wave_wavelets = [w for w in wavelets if w.wave_id == wave_id]
    update = conversation_update(wave_id, wave_wavelets, sequence_number)
    return [update] if update else []
