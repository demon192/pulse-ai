#!/usr/bin/env python3
"""Seed the configured datastore with the synthetic TeamPulse demo organisation.

Usage:
    python scripts/seed_demo_data.py            # seed the configured backend
    python scripts/seed_demo_data.py --no-reset # add without wiping first

The data backend comes from the environment (DATA_BACKEND=memory|firestore).
Seeding an in-memory backend is only useful inside a running process, so this
script is intended for Firestore (or the Firestore emulator).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings  # noqa: E402
from app.core.logging import configure_logging  # noqa: E402
from app.demo.seed import seed  # noqa: E402
from app.repositories.database import build_database  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Do not clear existing collections before seeding.",
    )
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(settings.log_level)

    if settings.environment == "production":
        print("Refusing to seed demo data into a production environment.", file=sys.stderr)
        return 2

    database = build_database(settings)
    counts = seed(database, reset=not args.no_reset)
    print(
        json.dumps(
            {
                "status": "seeded",
                "environment": settings.environment,
                "data_backend": settings.data_backend,
                "counts": counts,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
