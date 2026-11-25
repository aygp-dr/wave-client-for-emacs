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


def main() -> int:
    warnings.filterwarnings("ignore", message="Generating overly large repr")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", default="synthetic.db", help="SQLite file to (re)create")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--max-worlds", type=int, default=40)
    parser.add_argument("--edgy", action="store_true", help="arbitrary unicode text, not word salad")
    parser.add_argument("--minimal", action="store_true", help="one shrunk world covering every feature")
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
    blips = sum(len(w.blips) for w in world.waves)
    print(f"{db_path}: {len(parts)} world(s), {len(synthetic.known_users(world))} users, "
          f"{len(world.waves)} waves, {blips} blips, {len(world.states)} user states (seed {arguments.seed})")
    for name, ok in covered.items():
        print(f"  {'ok  ' if ok else 'MISS'} {name}")
    return 0 if all(covered.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
