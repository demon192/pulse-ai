#!/usr/bin/env python3
"""Seed the configured datastore with the synthetic TeamPulse demo organisation.

Usage:
    python scripts/seed_demo_data.py            # seed the configured backend
    python scripts/seed_demo_data.py --no-reset # add without wiping first
    python scripts/seed_demo_data.py --manager-email you@example.com

The seeded organisation is fictional and its addresses are @example.com, which
no real identity provider will ever issue. In Firebase auth mode the backend
maps a verified email to a seeded user, so a real sign-in matches nobody until
one of those addresses is yours: --manager-email points the manager persona at
an account you can actually sign in with. It changes demo data only, never an
authorisation rule.

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
    parser.add_argument(
        "--manager-email",
        metavar="ADDRESS",
        help=(
            "Give the manager persona (mgr-001) this email so a real Firebase "
            "sign-in resolves to it. Demo data only."
        ),
    )
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(settings.log_level)

    if settings.environment == "production":
        print("Refusing to seed demo data into a production environment.", file=sys.stderr)
        return 2

    database = build_database(settings)
    counts = seed(database, reset=not args.no_reset)

    manager_email = None
    if args.manager_email:
        address = args.manager_email.strip().lower()
        if "@" not in address:
            print(f"'{args.manager_email}' is not an email address.", file=sys.stderr)
            return 2
        clash = database.users.find_one(
            lambda item: item.email.lower() == address and item.id != "mgr-001"
        )
        if clash is not None:
            # Two users with one address would make the email-to-user mapping
            # ambiguous, and which one resolves would depend on iteration order.
            print(
                f"'{address}' is already {clash.id}'s address; refusing to "
                "create a duplicate.",
                file=sys.stderr,
            )
            return 2
        manager = database.users.require("mgr-001")
        database.users.save(manager.model_copy(update={"email": address}))
        manager_email = address

    print(
        json.dumps(
            {
                "status": "seeded",
                "environment": settings.environment,
                "data_backend": settings.data_backend,
                "counts": counts,
                "manager_email": manager_email,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
