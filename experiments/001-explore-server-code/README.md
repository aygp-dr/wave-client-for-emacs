# Experiment 001: Explore Server Code

Recover what the original 2009-10 project shipped on the "server side", and
where our FastAPI reconstruction (`src/wave_client_server/fedone.py`) departs
from it.

## Source

The Google Code Archive still serves the project's full Mercurial repository:

    https://storage.googleapis.com/google-code-archive-source/v2/code.google.com/wave-client-for-emacs/source-archive.zip
    sha256 1e387ec3a18b57b7a0717e7a683a73f7ac50ccc58d1b3bd14302798e231790d1

(`project.json` and `repo.json` beside it return 403.) The zip is the working
tree at tip plus `.hg/`: 101 changesets, rev 0 (2009-09-01) to rev 100
(2012-05-06), branches `default` and `direct-connect` (inactive, merged at
rev 38). `.hg/hgrc` held only `[paths] default = https://code.google.com/p/wave-client-for-emacs/`;
it is deleted before any `hg` command. The JARs are in the revlogs, not the
tip tree, because rev 35 deleted them.

`gmake run` repeats the whole extraction into a temp dir and regenerates
`results/`. Nothing from the archive is executed: hg only reads the store,
`javap` only disassembles.

## What was recovered (`results/`)

| file | revisions | note |
|---|---|---|
| `hg/client.clj.r{2,4,5,8,14}` | all 5 that touched it | added rev 2, deleted rev 35 |
| `hg/start-repl.sh.r{2,3,4}` | all 3 | r2 has the author's absolute path, as committed in 2009 |
| `hg/build.xml.r0` | 1 | ant build for "the Java client that emacs connects to"; gone by rev 2 |
| `hg/README.r2` | 1 | the README describing the Clojure architecture (unchanged through rev 29) |
| `hg/wave-client.el.r{4,14}` | 2 of 46 | the elisp side of the REPL bridge, first and last version |
| `hg/wave-protocol-README.r0` | 1 | "FedOne API library", wave-protocol 0.2, unmodified |
| `proto/*.proto` | | `common.proto`, `rpc.proto`, `waveclient-rpc.proto` from `fedone-server-0.2.jar`; the api jar's copies are byte-identical |
| `javap-summary.txt` | | class signatures, wire framing bytecode, constants |
| `hg-log.txt` | 101 changesets | |

JARs in history (rev 14 sizes): `fedone-api-0.2.jar` (506KB, "Google Wave
Reference Impl API" 0.2), `fedone-server-0.2.jar` (3.2MB, "Google Wave FedOne
Server" 0.2, Main-Class `ServerMain`), `clojure-1.0.0.jar`,
`protobuf-java-2.1.0.jar`, and two the old README did not list:
`clojure-contrib.jar` and `google-collect-1.0-rc2.jar`. None are copied here.

Timeline: rev 0-2 (2009-09) add jars and `client.clj`; rev 4 (2009-10-12)
"Create the emacs connection layer that uses the FedOne REPL"; rev 14
(2009-12-10) last `client.clj` change (`get-wave`); rev 15 starts the
`direct-connect` branch against wave.google.com (`/wfe` JSON, later browser
channel); rev 35 (2010-01-03) "Deleted no-longer necessary FedOne files";
rev 60 (2010-04-23) "Add beginnings of websocket-based client"; rev 90
(2010-05-18) "Convert (quickly) to proto bufs".

## Answers

**1. Client or server?** A client. `client.clj` (ns `wave-for-emacs.client`,
doc "Wave Client Code - starts REPL on socket") wraps FedOne's *client*
library, `waveclient.common.ClientBackend`, and starts
`clojure.contrib.server-socket/create-repl-server` on a port. The only
server in the picture is a stock FedOne 0.2 server the user ran separately:
README.r2 says "Right now, this Wave client cannot use an actual Wave server
... you have to do the temporary step of downloading, compiling and running
the wave-protocol FedOne test server." `fedone-server-0.2.jar` was on the
classpath only because `ClientBackend` lives in it (it also ships in the api
jar). The project never had server code of its own.

**2. How did it talk to Wave?** Through `ClientBackend(String userAtDomain,
String host, int port)`, which opens a `ClientRpcChannel` to the FedOne
server's client frontend (`--client_frontend_hostname` /
`--client_frontend_port`, elisp default port 9876). That transport is raw TCP
carrying binary protobuf, framed by `SequencedProtoChannel.sendMessage`:
little-endian uint32 total size, varint64 sequence number, length-prefixed
protobuf full type name (e.g. `waveserver.ProtocolOpenRequest`), then the
length-prefixed message. The service is `ProtocolWaveClientRpc` with
`Open(ProtocolOpenRequest) -> stream ProtocolWaveletUpdate` and
`Submit(ProtocolSubmitRequest) -> ProtocolSubmitResponse`; a streaming RPC
ends with `rpc.RpcFinished`. `client.clj` never touches that layer: it calls
`getIndexWave`, `ClientUtils/getIndexEntries` (id + digest), `getWave`,
`getConversationRoot(...).getParticipants`, `createConversationWave`, and in
r14 walks each document with a `DocInitializationCursor` proxy to emit
strings, `[type attrs]` and `end` markers, nested into s-expressions. There
is no websocket, HTTP or JSON anywhere in the 0.2 jars (no jetty, servlet or
websocket classes).

**3. Relationship to the Emacs client?** The Clojure process was the
client's backend, spawned and driven by Emacs. `wave-client.el` r4/r14:
`wave-client-start-fedone` runs `start-repl.sh JAVA PORT` (default 8123),
`wave-client-start-repl` connects with `open-network-stream`, then
`wave-client-eval` sends `prin1-to-string` of a Clojure form to the REPL,
appends `(flush)`, strips prompts and `nil`s, and `read-from-string`s the
reply (`elispify` turns maps into dotted pairs so this works). Architecture,
from README.r2: Emacs -> TCP REPL -> Clojure API -> FedOne client -> RPC ->
FedOne server. All of it was dropped in rev 35. The websocket client we run
today (`lisp/wave-client-websocket.el`, rev 60 onward) is unrelated to the
Clojure code: it speaks JSON to a websocket frontend of a *later* FedOne,
which is not in this archive.

**4. Clojure vs Python?** There is no original server to port. The Clojure
code is a 124-line REPL facade over a Java client library, superseded twice
in the project's own history. A Clojure port of our Python server is a fresh
implementation whose only fidelity target is what the 2010 websocket client
accepts; the `.proto` files here are the authoritative field numbers for that
JSON. Being on the JVM buys nothing from the recovered jars unless one wants
to run FedOne 0.2 itself, which speaks a different transport than the client.

## Divergences from fedone.py

The 0.2 jars predate the websocket client, so "divergence" here means from
FedOne 0.2; where the 2010 elisp forces the Python behaviour, that is noted.

1. **Transport and endpoint.** 0.2: raw TCP on `client_frontend_port`,
   binary protobuf, no path. 2010 README: `ws://my.fedone.server:9898/socket`.
   Ours: `/ws` on 9898. Neither `/socket` nor `/ws` can be checked against
   these jars.
2. **Envelope.** 0.2 frames as (size, seq, full type name, bytes). The
   JSON envelope `{version, sequenceNumber, messageType, messageJson}` comes
   from the elisp client, not from these jars; it keeps the same triple but
   uses short names (`ProtocolWaveletUpdate`) where 0.2 used full names
   (`waveserver.ProtocolWaveletUpdate`). fedone.py matches the elisp.
3. **Field numbers: all match.** `ProtocolOpenRequest` {1 participant_id,
   2 wave_id, 3 wavelet_id_prefix, 4 maximum_wavelets};
   `ProtocolWaveletUpdate` {1 wavelet_name, 2 applied_delta,
   3 commit_notice, 4 resulting_version}; `ProtocolWaveletDelta`
   {1 hashed_version, 2 author, 3 operation, 4 address_path};
   `ProtocolHashedVersion` {1 version int64, 2 history_hash bytes};
   `ProtocolWaveletOperation` {1 add_participant, 2 remove_participant,
   3 mutate_document {1 document_id, 2 document_operation}, 4 no_op};
   `ProtocolDocumentOperation` {1 component}; `Component` {1
   annotation_boundary, 2 characters, 3 element_start {1 type, 2 attribute
   {1 key, 2 value}}, 4 element_end, 5 retain_item_count,
   6 delete_characters, 7 delete_element_start, 8 delete_element_end,
   9 replace_attributes, 10 update_attributes}. fedone.py uses only
   update 1/2/4, delta 1/2/3, hashed version 1/2, operation 1/3, and
   component 2/3/4, all correctly.
4. **History hash.** 0.2 version zero hashes to the UTF-8 bytes of the
   wavelet URI (`HashedVersionZeroFactoryImpl`), later versions chain
   SHA-256 (`HashedVersionFactoryImpl`). fedone.py sends `""` everywhere.
   Only `HashedVersion.unsigned(v)` (empty hash) matches, and FedOne uses
   that just for index-wave deltas. The elisp client stores the hash but
   never checks it.
5. **Index wave id.** 0.2: `CommonConstants.INDEX_WAVE_ID = new WaveId("",
   "indexwave")` (empty domain). fedone.py and the elisp use
   `indexwave!indexwave`, presumably the later FedOne's value.
6. **Index wavelet contents.** 0.2 (`ClientFrontendImpl.createIndexDeltas`)
   builds index deltas only for `conv+root` wavelets: the root wavelet's
   participant add/remove deltas (original authors, `participantDeltasOnly`)
   plus digest edits to doc `digest` authored by `digest-author`, as minimal
   edits (`lengthOfCommonPrefix`, `createEditOp`) as the root text changes.
   fedone.py emits one delta per wave, authored by the wave's creator,
   holding all add-participants and the whole digest as one insertion.
7. **Wavelet folding.** 0.2 streams every wavelet of the wave that matches
   `wavelet_id_prefix`, each from version 0 with its real deltas. fedone.py
   folds all stored wavelets into one synthetic `conv+root` and ignores the
   prefix and `maximum_wavelets`.
8. **Commit notices and stream end.** 0.2 sends updates carrying only
   `commit_notice` (field 3, `waveletCommitted`) and ends streams with
   `RpcFinished`. fedone.py sends neither; the elisp would break on both
   (`(assert deltas)`, and `ecase` on unknown message types), so the later
   websocket frontend must have filtered them, or the client crashed.
9. **Document ids.** 0.2 `ClientUtils.DEFAULT_DOCUMENT_ID = "default"`;
   fedone.py writes `conversation` and `b+...` documents, following the
   conversation-manifest model the elisp adopted at rev 50. The 0.2 client
   library would not understand that layout, but the elisp needs it.
