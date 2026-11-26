"""Record a scripted session against a hixie-76 websocket (Jetty 7.1, 2010).

  python3 capture_hixie76.py HOST PORT PATH COOKIE_FILE OUT.jsonl STEPS.json

The draft-76 handshake: two keys whose digits divided by their space count,
packed big-endian with 8 random bytes, MD5 to the 16-byte server answer.
Frames are 0x00 <utf-8> 0xFF. Every frame, both directions, goes to OUT.jsonl.
"""

import hashlib
import http.cookiejar
import json
import random
import socket
import struct
import sys
import time


def make_key() -> tuple[str, int]:
    spaces = random.randint(1, 12)
    number = random.randint(0, 4294967295 // spaces)
    key = list(str(number * spaces))
    for _ in range(random.randint(1, 12)):
        key.insert(random.randint(0, len(key)), random.choice("!#$%&'()*+,-./:;<=>?@[]^_`{|}~"))
    for _ in range(spaces):
        key.insert(random.randint(1, len(key) - 1), " ")
    return "".join(key), number


def main(host: str, port: str, path: str, cookie_file: str, out_path: str, steps_path: str) -> None:
    jar = http.cookiejar.MozillaCookieJar(cookie_file)
    jar.load(ignore_discard=True, ignore_expires=True)
    cookie = "; ".join(f"{c.name}={c.value}" for c in jar)
    key1, number1 = make_key()
    key2, number2 = make_key()
    challenge = bytes(random.getrandbits(8) for _ in range(8))
    expected = hashlib.md5(struct.pack(">II", number1, number2) + challenge).digest()

    connection = socket.create_connection((host, int(port)), timeout=10)
    request = (f"GET {path} HTTP/1.1\r\nUpgrade: WebSocket\r\nConnection: Upgrade\r\n"
               f"Host: {host}:{port}\r\nOrigin: http://{host}:{port}\r\nCookie: {cookie}\r\n"
               f"Sec-WebSocket-Key1: {key1}\r\nSec-WebSocket-Key2: {key2}\r\n\r\n").encode() + challenge
    connection.sendall(request)
    buffer = b""
    while b"\r\n\r\n" not in buffer:
        buffer += connection.recv(4096)
    head, buffer = buffer.split(b"\r\n\r\n", 1)
    while len(buffer) < 16:
        buffer += connection.recv(4096)
    answer, buffer = buffer[:16], buffer[16:]
    status = head.split(b"\r\n", 1)[0].decode()
    started = time.monotonic()
    with open(out_path, "w") as out:
        def record(direction: str, payload: str) -> None:
            try:
                frame = json.loads(payload)
            except ValueError:
                frame = payload
            out.write(json.dumps({"t": round(time.monotonic() - started, 3), "dir": direction, "frame": frame}) + "\n")
            out.flush()

        record("handshake", json.dumps({"status": status, "challenge_ok": answer == expected}))
        if answer != expected:
            sys.exit(f"handshake failed: {status}")
        channel = ""
        for sequence, step in enumerate(json.load(open(steps_path)), start=1):
            # "$CHANNEL" in a step becomes the channel id the server last announced (field 7)
            text = json.dumps({"messageType": step["messageType"], "sequenceNumber": sequence,
                               "message": step["message"]}).replace("$CHANNEL", channel)
            connection.sendall(b"\x00" + text.encode() + b"\xff")
            record("send", text)
            deadline = time.monotonic() + step.get("wait", 3)
            while time.monotonic() < deadline:
                while b"\xff" in buffer:
                    frame, buffer = buffer.split(b"\xff", 1)
                    payload = frame.lstrip(b"\x00").decode("utf-8", "replace")
                    record("recv", payload)
                    try:
                        channel = json.loads(payload)["message"].get("7", channel)
                    except (ValueError, KeyError, AttributeError):
                        pass
                connection.settimeout(max(0.05, deadline - time.monotonic()))
                try:
                    chunk = connection.recv(65536)
                except socket.timeout:
                    continue
                if not chunk:
                    record("closed", "{}")
                    return
                buffer += chunk
    connection.close()


if __name__ == "__main__":
    main(*sys.argv[1:7])
