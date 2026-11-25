#!/usr/bin/env python3
"""Generate a reproducible synthetic Wave database that exercises every UI state.

Draws valid worlds from the Hypothesis strategies in
wave_client_server.synthetic (same seed, same data) and merges them until
every entry in UI_FEATURES is covered (hypothesis.find with coverage as the
predicate). --minimal also shrinks the result to a smallest covering batch.

Usage (needs the test extra):
  uv run --extra test python scripts/gen-synthetic-waves.py --db synthetic.db [--seed 1] [--edgy]
  WAVE_DATABASE_URL=sqlite:///./synthetic.db uv run wave-client-server   # then point Emacs at it
"""

from __future__ import annotations

import argparse
import random
import sys
import warnings
from pathlib import Path

from hypothesis import HealthCheck, Phase, settings
from hypothesis import find as hypothesis_find
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from wave_client_server import synthetic


def covering_batch(seed_value: int, max_worlds: int, edgy: bool, shrink: bool) -> list[synthetic.World]:
    """First batch of worlds (for this seed) whose union covers UI_FEATURES;
    with SHRINK, Hypothesis then minimises it."""
    phases = [Phase.generate, Phase.shrink] if shrink else [Phase.generate]
    return hypothesis_find(
        synthetic.world_batches(max_worlds=max_worlds, edgy=edgy),
        lambda batch: all(synthetic.coverage(synthetic.merge(batch)).values()),
        settings=settings(max_examples=2000, database=None, deadline=None, phases=phases,
                          suppress_health_check=list(HealthCheck)),
        random=random.Random(seed_value),
    )


def find_witnesses(db_url: str, world: synthetic.World) -> dict[str, dict[str, str]]:
    """For each UI feature, a (user, folder, wave) where the API shows it.
    Asked of the real API, so the Emacs acceptance test knows where to look."""
    import os
    os.environ["WAVE_DATABASE_URL"] = db_url
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker as make_session

    from wave_client_server.user_api import FOLDERS
    from wave_client_server.wave_server import app, get_db

    engine = create_engine(db_url)
    Session = make_session(bind=engine)

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    client = TestClient(app)

    def depth(blips, level=0):
        return max([level] + [depth(b["children"], level + 1) for b in blips])

    def flat(blips):
        for b in blips:
            yield b
            yield from flat(b["children"])

    row_checks = {
        "unread wave": lambda r: r["unread_count"] > 0,
        "fully read wave": lambda r: r["unread_count"] == 0 and r["blip_count"] > 1,
        "muted wave": lambda r: r["muted"],
        "tagged wave": lambda r: bool(r["tags"]),
        "public wave": lambda r: r["public"],
        "single-blip wave": lambda r: r["blip_count"] == 1,
        ">= 6 participants": lambda r: len(r["participants"]) >= 6,
        "title >= 60 chars": lambda r: len(r["title"]) >= 60,
    }
    view_checks = {
        "gadget, all columns voted": lambda v: any(all(g["votes"].values()) for b in flat(v["blips"]) for g in b["gadgets"]),
        # depth() counts the root as 1: 4 = root and three nested replies
        "reply nested 2 deep": lambda v: depth(v["blips"]) >= 4,
        "multi-line blip": lambda v: any(len(b["lines"]) >= 3 for b in flat(v["blips"])),
    }
    found: dict[str, dict[str, str]] = {}
    for user in synthetic.known_users(world):
        auth = (user.split("@")[0],) * 2
        folders = [f["name"] for f in client.get("/api/folders", auth=auth).json()]
        for folder in folders:
            for row in client.get("/api/waves", params={"folder": folder}, auth=auth).json():
                witness = {"user": user, "folder": folder, "wave": row["id"], "title": row["title"]}
                if folder in ("spam", "trash"):
                    found.setdefault(folder, witness)
                    continue
                if folder not in FOLDERS:
                    found.setdefault("custom folder", witness)
                if folder == "all" and row["archived"]:
                    found.setdefault("archived wave", witness)
                for name, check in row_checks.items():
                    if folder == "all" and check(row):
                        found.setdefault(name, witness)
                if folder == "all":
                    view = None
                    for name, check in view_checks.items():
                        if name not in found:
                            view = view or client.get(f"/api/waves/{row['id']}/view", auth=auth).json()
                            if check(view):
                                found[name] = witness
    app.dependency_overrides.pop(get_db, None)
    return found


def main() -> int:
    warnings.filterwarnings("ignore", message="Generating overly large repr")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", default="synthetic.db", help="SQLite file to (re)create")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--max-worlds", type=int, default=40)
    parser.add_argument("--edgy", action="store_true", help="arbitrary unicode text, not word salad")
    parser.add_argument("--minimal", action="store_true", help="shrink to a smallest covering batch")
    parser.add_argument("--witnesses", help="write feature -> {user, folder, wave} JSON here")
    arguments = parser.parse_args()

    parts = covering_batch(arguments.seed, arguments.max_worlds, arguments.edgy, arguments.minimal)
    world = synthetic.merge(parts)

    db_path = Path(arguments.db)
    db_path.unlink(missing_ok=True)
    engine = create_engine(f"sqlite:///{db_path}")
    from wave_client_server.wave_server import (
        Base,  # registers all tables, incl. user state
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    synthetic.write_world(session, world)
    session.close()

    covered = synthetic.coverage(world)
    if arguments.witnesses:
        import json
        witnesses = find_witnesses(f"sqlite:///{db_path.resolve()}", world)
        Path(arguments.witnesses).write_text(json.dumps(witnesses, indent=2, ensure_ascii=False) + "\n")
        missing = [name for name in [*synthetic.UI_FEATURES, "spam", "trash"] if name not in witnesses
                   and name not in ("spam", "trash", "custom folder", "archived wave")]
        print(f"witnesses -> {arguments.witnesses} ({len(witnesses)} features)" + (f"; none for {missing}" if missing else ""))
    blips = sum(len(w.blips) for w in world.waves)
    print(f"{db_path}: {len(parts)} world(s), {len(synthetic.known_users(world))} users, "
          f"{len(world.waves)} waves, {blips} blips, {len(world.states)} user states (seed {arguments.seed})")
    for name, ok in covered.items():
        print(f"  {'ok  ' if ok else 'MISS'} {name}")
    return 0 if all(covered.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
