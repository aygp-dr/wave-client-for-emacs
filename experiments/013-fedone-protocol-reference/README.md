# 013 — FedOne client/server protocol reference (2010)

What the server behind `ws://my.fedone.server:9898/socket` actually was, read
from its own source, and where `src/wave_client_server/fedone.py` (experiment
010) departs from it.

Labels: **[read]** means read in the upstream source at the cited revision.
**[inferred]** means a conclusion drawn from reading, not observed running.
Nothing upstream was built or run.

## Sources

| source | what it holds | 2010 history? |
|---|---|---|
| Google Code Archive, `wave-protocol`: <https://code.google.com/archive/p/wave-protocol>, source zip <https://storage.googleapis.com/google-code-archive-source/v2/code.google.com/wave-protocol/source-archive.zip> (224,109,516 bytes, Last-Modified 2016-03-23) | the whole Mercurial repo (`.hg/`), 1025 changesets, tip `1024:6a56af40d823` (2011-09-15) | **yes**, the only source with it |
| `apache/incubator-wave` (and identical `apache/incubator-retired-wave`), HEAD `e4cb87ffce3b` | Apache Wave git | no: the root commit `b3815a0` (2011-10-11) is "Initial check to svn. From …wave-protocol/source/ revision 6a56af40d823", a snapshot without history |

So the 2010 websocket frontend can be recovered, and all of it comes from the
hg repo in the archive zip. Revision numbers below are local hg revs of that
repo, with node ids so they can be checked against any other clone.

| rev | node | date | event |
|---|---|---|---|
| 148 | `92259daecb82` | 2010-03-17 | "first cut of websocket client/server protocol using JSON" (zamfi). JSON by `protobuf-java-format` `JsonFormat`: **field names**, not numbers |
| 198 | `a4a71c8f385c` | 2010-04-23 | `run-config.sh.example` gains `WEBSOCKET_SERVER_PORT=9898` |
| 206 | `4cddb1c04a9f` | 2010-05-07 | "Client/Server protocol wavelet snapshotting": `snapshots`, `marker`, `channel_id` |
| 228 | `024138e3c9ad` | 2010-08-04 | "Update FedOne to work with the new library jars": websocket JSON switches to protostuff `ReflectionNumericJSON` (**field numbers**), envelope `version` 0 → 1 |
| 239 | `6442fda60d98` | 2010-08-13 | Jetty 7.0.2 → 7.1.6 (adds hixie-76) |
| 245 | `7caba36f3597` | 2010-08-13 | websocket servlet moves from `/` to `/socket` |
| 252 | `d645c021bee8` | 2010-08-18 | index-wave logic extracted to `IndexWave.java` (same behaviour) |
| 333 | `1091b44fe9d9` | 2010-09-10 | `maximum_wavelets` (field 4) removed from the open request |
| 350 | `f6acb10166b8` | 2010-09-14 | last revision before the break below |
| 351 | `1e4eb6366bab` | 2010-09-14 | "Removes snapshot parameter …; all clients accept snapshots": conversation wavelets now arrive as snapshots with zero deltas |
| 487 | `7492587f1269` | 2010-10-12 | `examples.fedone` renamed to `box` (Wave in a Box) |

### Which server the Emacs client was written for [inferred]

The client (`lisp/wave-client-websocket.el`) reads `messageJson` keyed by field
number (`:1`, `:2`, …), so it needs rev ≥ 228; before that, keys were names
like `"wavelet_name"`. It asserts that every `ProtocolWaveletUpdate` carries
deltas (`(assert deltas)`) and never reads field 5 (`snapshot`). From rev 351
on, every non-index wavelet arrives as a snapshot with no deltas, so opening a
wave fails. **The compatible window is rev 228 to rev 350, 2010-08-04 to
2010-09-14.** The reference below describes that window and cites rev 228 or
rev 333 files. In this window the client never sets `snapshots` (field 5), so it
gets deltas.

## Protocol reference (rev 228–350)

### Transport

- **Port** 9898: `WEBSOCKET_SERVER_PORT=9898` in `run-config.sh.example`
  (rev 198 onward, lines 23–25), passed to the server as
  `--http_frontend_port` (`run-server.sh`, rev 228 line 29). [read]
- **Path**: from rev 228 to 244 the `WaveWebSocketServlet` is mounted at `/`
  (`ServerRpcProvider.java` rev 228 line 292), so every path is accepted. From
  rev 245 it is `/socket` (`ServerRpcProvider.java` rev 333 line 308). The Java
  console client always dialled `/socket` (`WebSocketClientChannel.java` rev 228
  line 64). [read]
- **Handshake**: Jetty `jetty-websocket-7.0.2.v20100331` until rev 238. Its
  classes contain only `WebSocket-Origin`, `WebSocket-Location` and
  `WebSocket-Protocol`, so it speaks hixie-75 only. `jetty-websocket-7.1.6.v20100715`
  from rev 239 adds `Sec-WebSocket-Key1/Key2` (hixie-76) and keeps 75. The
  Emacs client binds `websocket-use-v75` to `t` in `wave-client-ws-connect`,
  which works on both. [read from the class-file constant pools]
- **Frames**: 1 MB buffer, idle timeout −1 (`ServerRpcProvider.java` rev 228
  lines 290–291). A message is never split across frames (`TODO(zamfi)`). [read]

### Envelope

`WebSocketChannel.java` rev 228 (lines 41, 84, 96–134) and `MessageWrapper.java`:

```json
{"version": 1, "sequenceNumber": <long>, "messageType": "<proto short name>", "messageJson": "<string>"}
```

- The server writes the envelope with Gson 1.4 (`gson.toJson(wrapper)`).
  `messageType` is `message.getDescriptorForType().getName()`, e.g.
  `ProtocolWaveletUpdate`, `ProtocolSubmitResponse`, `RpcFinished`. [read]
- The server sends `version` 1 and never checks `version` on input. [read]
- `sequenceNumber` is chosen by the client for each RPC. Every response to that
  RPC, streaming ones included, is sent back with the same number
  (`ServerRpcProvider.java` rev 228 lines 148–196). Reusing a number that is
  still active throws `IllegalStateException`. [read]
- Gson escapes HTML characters by default (`=` becomes `=` and so on).
  That would explain the client's `wave-client-ws-fixup-control-codes`, which
  doubles backslashes before parsing the inner JSON. [inferred]

### messageJson: protostuff `ReflectionNumericJSON`

The class is `com.dyuproject.protostuff.json.ReflectionNumericJSON` from
`third_party/codegen/protostuff/protostuff.jar` (protostuff r672). It is
constructed in `WebSocketChannel.java` rev 228 line 84 over the
`MODULE_CLASSES` list (lines 47–72). Read from its bytecode with `javap`:

- Keys are field **numbers** as strings (`String.valueOf(PropertyMeta.getNumber())`;
  input goes through `Integer.parseInt`).
- An optional field is written only when its generated `has…` flag is set
  (`MessagePropertyAccessor$FieldAccess.getValue` returns null unless `_has` is
  true). An empty repeated field is omitted (`RepeatedFieldAccess` returns null
  when `List.size()==0`). Explicitly set defaults are still written, so
  `setMarker(false)` produces `"6": false`.
- `bytes` fields (`history_hash`) are **base64**, via Jackson
  `JsonGenerator.writeBinary` (`InlineValue$7`). An empty hash is `""`.
- Repeated fields are JSON arrays, nested messages are objects, `bool` is
  `true`/`false`, `int64` is a number.

### Messages and field numbers

Verbatim copies are in `proto/`: `waveclient-rpc.proto` (rev 228),
`waveclient-rpc.r333.proto` (rev 333), `rpc.proto` (rev 228), and
`federation.protodevel` (rev 333). The federation proto is identical to rev 202;
at rev 228 it shipped compiled inside `wave-libraries/federation-2010-08-04.jar`.

```
ProtocolOpenRequest            (waveclient-rpc.proto r228 :50)
  1 participant_id   string   required
  2 wave_id          string   required   "domain!id", e.g. "indexwave!indexwave"
  3 wavelet_id_prefix string  repeated   empty = all
  4 maximum_wavelets int32    optional   (removed r333, "OBSOLETE = 4")
  5 snapshots        bool     optional [default=false]
  6 known_wavelets   WaveletVersion repeated  (resync; disabled, TODO(arb))

ProtocolWaveletUpdate          (:93)
  1 wavelet_name     string   required   wave://<wavelet-domain>/[<wave-domain>!]<wave-id>/<wavelet-id>
  2 applied_delta    ProtocolWaveletDelta repeated
  3 commit_notice    ProtocolHashedVersion optional
  4 resulting_version ProtocolHashedVersion optional
  5 snapshot         WaveletSnapshot optional
  6 marker           bool     optional [default=false]
  7 channel_id       string   optional

ProtocolSubmitRequest          (:126)
  1 wavelet_name     string   required
  2 delta            ProtocolWaveletDelta required
  3 channel_id       string   optional

ProtocolSubmitResponse         (:138)
  1 operations_applied int32  required
  2 error_message    string   optional
  3 hashed_version_after_application ProtocolHashedVersion optional

ProtocolWaveletDelta           (federation.protodevel :41)
  1 hashed_version   ProtocolHashedVersion required   (the pre-version)
  2 author           string   required
  3 operation        ProtocolWaveletOperation repeated
  4 address_path     string   repeated

ProtocolHashedVersion          (:73)
  1 version          int64    required
  2 history_hash     bytes    required

ProtocolWaveletOperation       (:82)   exactly one set
  1 add_participant    string
  2 remove_participant string
  3 mutate_document    MutateDocument { 1 document_id string; 2 document_operation ProtocolDocumentOperation }
  4 no_op              bool

ProtocolDocumentOperation      (:106)
  1 component        Component repeated
Component                      (:112)   exactly one set
  1 annotation_boundary AnnotationBoundary { 1 empty bool; 2 end string*; 3 change KeyValueUpdate* }
  2 characters        string
  3 element_start     ElementStart { 1 type string; 2 attribute KeyValuePair* }
  4 element_end       bool
  5 retain_item_count int32
  6 delete_characters string
  7 delete_element_start ElementStart
  8 delete_element_end bool
  9 replace_attributes ReplaceAttributes { 1 empty bool; 2 old_attribute KeyValuePair*; 3 new_attribute KeyValuePair* }
 10 update_attributes UpdateAttributes { 1 empty bool; 2 attribute_update KeyValueUpdate* }
  KeyValuePair   { 1 key string; 2 value string }
  KeyValueUpdate { 1 key string; 2 old_value string?; 3 new_value string? }

RpcFinished                    (rpc.proto r228 :65)
  1 failed bool required; 2 error_text string optional
CancelRpc                      (:55)  empty; client→server
```

`Open` is marked `is_streaming_rpc` (extension 1003). It never completes on
success. On failure the server sends `RpcFinished{failed:true}`
(`ServerRpcController.java` rev 228 lines 123, 174–181). [read]

### Wavelet names

`IdURIEncoderDecoder.waveletNameToURIPath` (rev 202 lines 81–94) builds
`<wavelet domain>/` + (`<wave domain>!` only when it differs from the wavelet
domain) + `<wave id>/<wavelet id>`. `URIEncoderDecoder` leaves
`:@!$&'()*+,;=-._~` and alphanumerics unescaped, so `+` stays literal. [read]

- conversation root: `wave://localhost/w+abc123/conv+root`
- index wavelet: `INDEX_WAVE_ID = new WaveId("indexwave","indexwave")`
  (`CommonConstants.java` rev 202 line 33). The index wavelet for wave
  `localhost!w+abc123` is `WaveletName.of(INDEX_WAVE_ID, WaveletId.deserialise("localhost!w+abc123"))`
  (`ClientFrontendImpl.java` rev 228 line 139), which gives
  `wave://localhost/indexwave!indexwave/w+abc123`.
- dummy, for marker and channel-id messages: `wave://<domain>/<wave id>/dummy+root`
  (`ClientFrontendImpl.java` rev 228 lines 646–650).

### Hashed versions

- Version 0 of a real wavelet has a history hash equal to the UTF-8 bytes of
  its wavelet URI (`HashedVersionZeroFactoryImpl.java` rev 228 lines 50–55).
  On the wire it is base64 of `wave://localhost/w+abc123/conv+root`. [read]
- After that, the hash is the first 160 bits of SHA-256(previous hash ‖ applied
  delta bytes) (`HashedVersionFactoryImpl.java` rev 228 lines 36–53). [read]
- Index-wave deltas use `HashedVersion.unsigned(v)`, which is an empty hash and
  serializes as `""` (`HashedVersion.java` rev 228 lines 77–79). [read]

### Open: what the server sends

`ClientFrontendImpl.openRequest`, rev 228 lines 179–292 (rev 333 lines 143–250
behave the same), with `WaveClientRpcImpl.open`, rev 228 lines 73–141:

1. It subscribes the participant to every wavelet of the wave that it is on and
   that matches a prefix. Prefix `""` matches all. [read]
2. For **each** wavelet it sends one `ProtocolWaveletUpdate` with the
   **full delta history from version 0** to the current version
   (`waveletProvider.getHistory(source, version0, endVersion)`), plus
   `"4"` the resulting version, `"6": false`, and `"7": "chN"`. A snapshot is
   sent instead only when the client asked for one with `snapshots=true`, or at
   rev ≥ 351. The order follows the set's iteration order. [read]
3. If there were no wavelets, it sends one channel-id-only update:
   `{"1": "wave://…/dummy+root", "6": false, "7": "chN"}` (lines 281–286). [read]
4. It **always** ends with a marker:
   `{"1": "wave://…/dummy+root", "6": true}` (no deltas, no version; lines 288–290). [read]
5. Afterwards, new deltas on subscribed wavelets go to the same channel
   (`UserManager.onUpdate`, rev 333 lines 285–306) as updates with
   `"2"`, `"4"` and `"6": false`, without `"7"`. [read]

The open request carries no "caught up" message other than the marker, and
there is none for the index wave either.

With the 2010 Emacs client, the marker and channel-id updates have no `"2"`,
so `(assert deltas)` in `wave-client-ws-wavelet-callback` signals inside the
process filter. That happens after every real wavelet has been applied, so the
result is noise, not lost data. [inferred]

### Index wave (`indexwave!indexwave`)

The index wave is not stored. It is computed for each participant in
`ClientFrontendImpl` (rev 228 lines 230–247, 430–447, 548–643), which moved
unchanged into `IndexWave.java` (rev 333 lines 99–111, 189–239):

- There is one index wavelet for each **conversation-root** wavelet (`conv+root`,
  same domain as the wave) that the participant is on. Its source is that root
  wavelet. Other wavelets are not indexed (`isConversationRootWavelet`, line 144).
- Its deltas, from version 0 with unsigned hashes:
  1. one **digest delta**, if the digest is non-empty: author
     **`digest-author`**, a single `mutate_document` on doc **`digest`** whose
     doc op is a plain edit from the old digest to the new one (retain the
     common prefix, `delete_characters` the rest of the old, `characters` the
     new). On open the old digest is `""`, so the op is `[{"2": digest}]`, with
     no element wrapper;
  2. then, for each source delta that contained add/remove-participant ops, a
     delta holding **only those ops**, keeping the original author.
- The **digest** text is `ClientUtils.renderSnippet(docs, 80)`: the characters
  of each blip document in `conversation` manifest order, stopping once 80
  characters are collected. It is then cut at the first `\n`, to at most 80
  characters (`digest()`, rev 228 lines 538–545). If there is no `conversation`
  doc, it is all characters of all documents (`ClientUtils.java` rev 228 lines
  279–288). [read]
- When a source wavelet changes, the participant also gets live index deltas:
  a digest edit and any participant changes (lines 430–447). [read]

### Conversation wavelet content (what histories looked like)

The server stores whatever clients submitted. The FedOne console client wrote
these shapes (`ClientBackend.createConversationWave` rev 228 lines 316–335,
`ClientUtils.createAppendBlipDelta` lines 146–172) [read]:

- create: `[add_participant(me), mutate "conversation" <conversation></conversation>]`
- each blip: `[mutate b+X (empty op), mutate b+X <body><line></line>text</body>, mutate "conversation" retain(n-1) <blip id=b+X></blip> retain(1)]`
- adding a participant is a separate delta of `add_participant` ops.

### Submit

`WaveClientRpcImpl.submit`, rev 228 lines 144–183, and
`ClientFrontendImpl.submitRequest`, lines 344–371 [read]:

- The wavelet name is decoded with the URI codec. A wavelet of
  `indexwave!indexwave` is rejected as read-only.
- The delta goes to the wave server, which transforms it, checks the hash and
  applies it.
- The response on the submit's `sequenceNumber` is `ProtocolSubmitResponse`:
  `{"1": opsApplied, "3": {"1": v, "2": "<b64>"}}` on success, or
  `{"1": 0, "2": "<error>"}` on failure. A non-streaming RPC ends with that
  single message.
- The applied delta is also sent as a `ProtocolWaveletUpdate` to every open
  channel subscribed to the wavelet. Echo suppression is keyed on
  `channel_id`. The Emacs client never sends field 3, so `findSubscription(…, null)`
  matches nothing and **the submitter gets its own delta back**
  (`UserManager.java` rev 333 lines 259–268, 362–386). The client relies on
  that echo: `wave-update.el` only sends, and never applies locally. [read
  for the server; inferred that this is what the client depended on]

## Divergences from fedone.py (and the websocket handler that calls it)

`fedone.py` = `src/wave_client_server/fedone.py` (experiment 010).
`wave_server.py` = `src/wave_client_server/wave_server.py`. Both are compared
as of commit `b1432fa`. Uncommitted work in progress at the time of writing
(threads, gadget votes) is not covered. Upstream's manifest vocabulary already
includes `thread` (`DocumentConstants.THREAD`, rev 202 line 43). Impact is
judged against the 2010 Emacs client as committed in `lisp/`.

| # | item | original (citation) | ours | impact |
|---|---|---|---|---|
| 1 | websocket path | `/` (any path), rev 228–244; `/socket` from rev 245 (`ServerRpcProvider.java` r228:292, r333:308) | `/ws` only (`wave_server.py` `@app.websocket("/ws")`) | **breaks** `README.original`'s `ws://…:9898/socket`. Works only with the repo's own `/ws` setting |
| 2 | handshake | hixie-75 (Jetty 7.0.2, ≤ rev 238); hixie-75/76 (Jetty 7.1.6, ≥ rev 239) | RFC 6455 behind the experiment 009 shim | none (009 handles it) |
| 3 | envelope `version` | `1` (`WebSocketChannel.java` r228:41) | `0` (`fedone.py` `wavelet_update`) | none: neither side reads it |
| 4 | trailing marker | always `{"1":"…/dummy+root","6":true}` after the initial updates (`ClientFrontendImpl.java` r228:288–290) | none | none. Ours is quieter: the original made the client's `(assert deltas)` signal on every open [inferred] |
| 5 | channel-id-only update when no wavelets match | `{"1":"…/dummy+root","6":false,"7":"chN"}` (r228:281–286) | nothing sent | none (same assert noise avoided) |
| 6 | fields `6`/`7` on data updates | `"6": false`, `"7": "chN"` on every initial update (`WaveClientRpcImpl.java` r228:107–110) | omitted | none: the client reads only `1`, `2`, `4` |
| 7 | history hash | base64 bytes: version 0 = base64(UTF-8 wavelet URI), then SHA-256/160 chain; index wave `""` (`HashedVersionZeroFactoryImpl` r228:50–55, `HashedVersionFactoryImpl` r228:36–53, protostuff `InlineValue$7`) | `""` everywhere | cosmetic. The client echoes the hash in submits: a real server would reject `""`, ours does not check |
| 8 | index wavelet delta layout | delta 0 by **`digest-author`**: `[mutate digest [{"2": digest}]]`, omitted when the digest is empty; then one participant-only delta per source delta, original authors (`IndexWave.java` r333:99–111, 189–239) | one delta by the wave's creator: `[add_participant…, mutate digest [{"2": digest}]]` | cosmetic. The client takes the wavelet creator from the first delta's author, so against the original the inbox "creator" column would read `digest-author`. 010's declared client change, creator = wavelet creator, only gives real names against our server |
| 9 | digest text | blip characters in manifest order, ≥ 80 collected, cut at first `\n`, ≤ 80 chars (`ClientFrontendImpl.java` r228:481, 538–545; `ClientUtils.renderSnippet` r228:279) | strings of the stored `digest` (or `main`) doc joined with spaces, no length cap | cosmetic |
| 10 | which wavelets are indexed | one index wavelet per **conv+root** wavelet the user participates in (r228:129–147); index wavelet id = wave id | one per wave in the DB, regardless of the requesting participant | cosmetic for one user. Ours ignores `participant_id` (field 1) entirely [read in `wave_server.py`: only field `"2"` is used] |
| 11 | wavelets per wave on open | one update **per wavelet** (any id matching the prefixes), each with its own full history (r228:210–277) | all stored wavelets folded into one `conv+root` update; replies become `b+` blips | none for rendering. It is a modelling difference: original data never had one wavelet per reply |
| 12 | conversation delta shapes | client-submitted history, e.g. `[add me, <conversation/>]`, then per blip `[empty op, <body><line/>text</body>, manifest insert]` (`ClientBackend.java` r228:316–335, `ClientUtils.java` r228:146–172) | `[add all participants, full manifest]`, then one `mutate` per blip | none: same final documents, version chaining verified in 010 |
| 13 | `+` in wavelet URIs | unescaped (`URIEncoderDecoder` NOT_ESCAPED) | unescaped | match |
| 14 | `sequenceNumber` on responses | echoes the request's (`ServerRpcProvider.java` r228:148–196) | echoes the request's | match |
| 15 | open errors | `RpcFinished {"1": true, "2": text}` on the same channel (`ServerRpcController.java` r228:123) | nothing / silent | none: the client's `ecase` would signal on `RpcFinished` anyway |
| 16 | live updates after open | streaming: new deltas on subscribed wavelets and index-wave digest edits keep arriving on the open channel (`UserManager.java` r333:285–306) | open is one-shot. The REST submit path broadcasts an update with `"2": []` to every socket (`wave_server.py` submit handler) | **breaks** live update. The empty-deltas broadcast also trips `(assert deltas)`. Other users' edits appear only after reopening |
| 17 | websocket submit | `ProtocolSubmitResponse` on the submit's sequence number, plus the applied delta echoed to the submitter's open channel (`WaveClientRpcImpl.java` r228:144–183; `UserManager.java` r333:259–268) | logged and dropped (`wave_server.py` `ProtocolSubmitRequest` branch) | **breaks** editing from Emacs: the client never applies its own delta and waits for the echo. The missing response itself is harmless: the client registers no callback for it |
| 18 | `ProtocolOpenRequest` fields read | 1, 2, 3, 5 (6 disabled) | only 2 | none for the 2010 client, which sends 1, 2, 3 |
| 19 | JSON escaping | Gson HTML-escapes the envelope; inner JSON from Jackson | Python `json.dumps` (ASCII-escapes non-ASCII) | none observed [inferred: the client's control-code fixup was written for Gson's output] |

Items 16 and 17 are in `wave_server.py`, not `fedone.py`. They are listed
because "the server the client talked to" covers both. Item 1 concerns the
transport. The synthesis that experiment 010 conjectured (items 8–12) matches
the original in the respects the client checks: chained versions from 0,
deltas present, `digest` doc, index wavelet ids = wave ids. It differs only in
authorship and digest text.

## Reproducing

```sh
curl -O https://storage.googleapis.com/google-code-archive-source/v2/code.google.com/wave-protocol/source-archive.zip
unzip -q source-archive.zip && cd wave-protocol
HGRCPATH= uvx --from mercurial hg log -k websocket        # the history above
HGRCPATH= uvx --from mercurial hg cat -r 228 src/org/waveprotocol/wave/examples/fedone/waveserver/ClientFrontendImpl.java
```

The protostuff findings come from `javap -c -p` on classes extracted from
`hg cat -r 228 third_party/codegen/protostuff/protostuff.jar`. The Jetty
handshake findings come from grepping header names in the classes of
`third_party/runtime/jetty/jetty-websocket-*.jar` at revs 202 and 333.
