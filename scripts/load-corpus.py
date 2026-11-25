#!/usr/bin/env python3
"""Load the static mock corpus (resources/corpus/waves.json) into a database.

Offline and deterministic: the corpus is checked in, nothing is generated or
fetched. Refuses to load a corpus that breaks a validity rule.

Usage (needs the test extra, for synthetic.World):
  uv run --extra test python scripts/load-corpus.py --db corpus.db
  WAVE_DATABASE_URL=sqlite:///./corpus.db uv run wave-client-server
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from wave_client_server import corpus, synthetic


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", default="corpus.db", help="SQLite file to (re)create")
    parser.add_argument("--corpus", default=str(corpus.CORPUS_PATH))
    arguments = parser.parse_args()

    data = corpus.load(arguments.corpus)
    broken = corpus.problems(data)
    if broken:
        print("corpus is invalid:", *broken, sep="\n  ", file=sys.stderr)
        return 1

    db_path = Path(arguments.db)
    db_path.unlink(missing_ok=True)
    engine = create_engine(f"sqlite:///{db_path}")
    from wave_client_server.wave_server import (
        Base,  # registers all tables, incl. user state
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    corpus.write(session, data)
    session.close()

    world = corpus.to_world(data)
    covered = synthetic.coverage(world)
    blips = sum(len(w.blips) for w in world.waves)
    print(f"{db_path}: {len(synthetic.known_users(world))} users, {len(world.waves)} waves, "
          f"{blips} blips, {len(world.states)} user states, {len(data['hn_snapshot'])} HN stories")
    for name, ok in covered.items():
        print(f"  {'ok  ' if ok else 'MISS'} {name}")
    return 0 if all(covered.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
