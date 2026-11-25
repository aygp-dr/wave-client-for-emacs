#!/usr/bin/env python3
"""Generate mock user avatars as SVG: a shared resource for the mock servers
(Python and Clojure) and the Emacs client.

Deterministic: the same address always yields the same file, so regenerating
produces no diff. Addresses are scanned from the seed data, plus a few fixed
entries. Stdlib only.

Output (resources/avatars/):
  <address>.svg     initials on a colour derived from the address
  default.svg       grey silhouette, for unknown participants
  public.svg        globe, for the public-wave participant
  manifest.json     {"size": 64, "default": "default.svg", "avatars": {address: file}}

Usage: python3 scripts/gen-avatars.py [--out resources/avatars]
"""

from __future__ import annotations

import argparse
import colorsys
import hashlib
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SEED_SOURCES = ["scripts/seed.sql", "seeds/*.json", "scripts/*.py", "src/wave_client_server/*.py"]
ADDRESS_PATTERN = re.compile(r"\b([a-z0-9][a-z0-9._+-]*@(?:localhost|[a-z0-9-]+\.local))\b")
FIXED_ADDRESSES = ["admin@localhost"]
PUBLIC_ADDRESS = "public@localhost"
SIZE = 64


def scan_addresses() -> list[str]:
    addresses = set(FIXED_ADDRESSES)
    for pattern in SEED_SOURCES:
        for path in PROJECT_ROOT.glob(pattern):
            addresses.update(ADDRESS_PATTERN.findall(path.read_text(errors="ignore")))
    addresses.discard(PUBLIC_ADDRESS)
    return sorted(addresses)


def colour_for(address: str) -> str:
    """Stable mid-saturation colour; hue from the address hash."""
    digest = hashlib.sha256(address.encode()).digest()
    hue = int.from_bytes(digest[:2], "big") / 65535
    lightness = 0.42 + (digest[2] / 255) * 0.12
    red, green, blue = colorsys.hls_to_rgb(hue, lightness, 0.55)
    return f"#{round(red * 255):02x}{round(green * 255):02x}{round(blue * 255):02x}"


def initials_for(address: str) -> str:
    local_part = address.split("@", 1)[0]
    words = [word for word in re.split(r"[._+-]+", local_part) if word]
    if len(words) >= 2:
        return (words[0][0] + words[1][0]).upper()
    word = words[0] if words else "?"
    return (word[0].upper() + (word[1] if len(word) > 1 else "")).strip()


def initials_svg(address: str) -> str:
    background = colour_for(address)
    initials = initials_for(address)
    font_size = 30 if len(initials) == 1 else 26
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{SIZE}" height="{SIZE}" viewBox="0 0 {SIZE} {SIZE}">
  <title>{address}</title>
  <rect width="{SIZE}" height="{SIZE}" rx="6" fill="{background}"/>
  <text x="50%" y="50%" dy="0.35em" text-anchor="middle" fill="#ffffff"
        font-family="Helvetica, Arial, sans-serif" font-size="{font_size}" font-weight="bold">{initials}</text>
</svg>
"""


DEFAULT_SVG = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{SIZE}" height="{SIZE}" viewBox="0 0 {SIZE} {SIZE}">
  <title>unknown participant</title>
  <rect width="{SIZE}" height="{SIZE}" rx="6" fill="#e3e8ee"/>
  <circle cx="32" cy="25" r="12" fill="#a7b4c2"/>
  <path d="M10 58 C10 42 20 38 32 38 C44 38 54 42 54 58 Z" fill="#a7b4c2"/>
</svg>
"""

PUBLIC_SVG = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{SIZE}" height="{SIZE}" viewBox="0 0 {SIZE} {SIZE}">
  <title>{PUBLIC_ADDRESS}</title>
  <rect width="{SIZE}" height="{SIZE}" rx="6" fill="#3b78c4"/>
  <g fill="none" stroke="#ffffff" stroke-width="2.5">
    <circle cx="32" cy="32" r="18"/>
    <ellipse cx="32" cy="32" rx="8" ry="18"/>
    <path d="M14 32 H50 M17 23 H47 M17 41 H47"/>
  </g>
</svg>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=str(PROJECT_ROOT / "resources" / "avatars"))
    output_dir = Path(parser.parse_args().out)
    output_dir.mkdir(parents=True, exist_ok=True)

    avatars: dict[str, str] = {}
    for address in scan_addresses():
        file_name = f"{address}.svg"
        (output_dir / file_name).write_text(initials_svg(address))
        avatars[address] = file_name
    (output_dir / "default.svg").write_text(DEFAULT_SVG)
    (output_dir / "public.svg").write_text(PUBLIC_SVG)
    avatars[PUBLIC_ADDRESS] = "public.svg"

    manifest = {"size": SIZE, "default": "default.svg", "avatars": dict(sorted(avatars.items()))}
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"{len(avatars)} avatars + default -> {output_dir}")


if __name__ == "__main__":
    main()
