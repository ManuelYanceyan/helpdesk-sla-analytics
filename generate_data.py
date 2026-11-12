"""Generate a reproducible synthetic IT helpdesk dataset.

All tickets, agents and customer interactions are fictional. Timestamps cover
the 2025 calendar year. The same seed always produces the same CSV file.
"""

from __future__ import annotations

import argparse
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
TICKETS_FILE = DATA_DIR / "tickets.csv"

SEED = 7
N_TICKETS = 480
START = datetime(2025, 1, 1, 0, 0, 0)
DAYS = 365

PRIORITIES = ("Low", "Medium", "High", "Critical")
PRIORITY_WEIGHTS = (30, 40, 22, 8)

# First-response and full-resolution targets in minutes. These are illustrative
# service levels for the demo, not a real client contract.
RESPONSE_TARGET_MIN = {"Low": 480, "Medium": 240, "High": 60, "Critical": 15}
RESOLUTION_TARGET_MIN = {"Low": 2880, "Medium": 1440, "High": 480, "Critical": 240}
RESPONSE_BREACH_RATE = {"Low": 0.18, "Medium": 0.14, "High": 0.11, "Critical": 0.08}
RESOLUTION_BREACH_RATE = {"Low": 0.25, "Medium": 0.20, "High": 0.15, "Critical": 0.10}

CATEGORIES = ("Hardware", "Software", "Network", "Access", "Email", "Other")
CATEGORY_WEIGHTS = (22, 26, 18, 17, 12, 5)

CHANNELS = ("Email", "Portal", "Phone", "Chat")
CHANNEL_WEIGHTS = (38, 30, 22, 10)

AGENTS = (
    "Agent Rivera", "Agent Campos", "Agent Solis",
    "Agent Neira", "Agent Paredes", "Agent Quispe",
)

STATUSES = ("Closed", "Pending", "Open")
STATUS_WEIGHTS = (82, 9, 9)


def _weighted_choice(rng: random.Random, options, weights):
    return rng.choices(options, weights=weights, k=1)[0]


def _iso(moment: datetime | None) -> str:
    return moment.isoformat(timespec="seconds") if moment is not None else ""


def generate_tickets(
    out_dir: Path | str = DATA_DIR,
    n_tickets: int = N_TICKETS,
    seed: int = SEED,
) -> dict[str, int]:
    """Write ``tickets.csv`` with synthetic helpdesk activity."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)

    created_times = [
        START + timedelta(minutes=rng.randrange(0, DAYS * 24 * 60))
        for _ in range(n_tickets)
    ]
    created_times.sort()

    rows: list[dict] = []
    for index, created_at in enumerate(created_times, start=1):
        priority = _weighted_choice(rng, PRIORITIES, PRIORITY_WEIGHTS)
        category = _weighted_choice(rng, CATEGORIES, CATEGORY_WEIGHTS)
        channel = _weighted_choice(rng, CHANNELS, CHANNEL_WEIGHTS)
        agent = rng.choice(AGENTS)
        status = _weighted_choice(rng, STATUSES, STATUS_WEIGHTS)

        response_target = RESPONSE_TARGET_MIN[priority]
        if rng.random() < RESPONSE_BREACH_RATE[priority]:
            response_minutes = rng.uniform(response_target * 1.05, response_target * 3.0)
        else:
            response_minutes = rng.uniform(1.0, response_target * 0.9)

        # A share of open tickets has not received a first response yet. They
        # count as response-SLA breaches because the target has elapsed.
        if status == "Open" and rng.random() < 0.35:
            first_response_at = None
        else:
            first_response_at = created_at + timedelta(minutes=round(response_minutes, 1))

        resolved_at = None
        resolution_minutes = None
        resolution_target = RESOLUTION_TARGET_MIN[priority]
        reopened = 0
        satisfaction = None

        if status == "Closed":
            if rng.random() < RESOLUTION_BREACH_RATE[priority]:
                resolution_minutes = rng.uniform(
                    resolution_target * 1.05, resolution_target * 2.5
                )
            else:
                resolution_minutes = rng.uniform(
                    resolution_target * 0.15, resolution_target * 0.95
                )

            if first_response_at is not None:
                elapsed_response = (first_response_at - created_at).total_seconds() / 60
                resolution_minutes = max(
                    resolution_minutes, elapsed_response + rng.uniform(3, 45)
                )

            resolved_at = created_at + timedelta(minutes=round(resolution_minutes, 1))
            reopened = 1 if rng.random() < 0.08 else 0

            if rng.random() < 0.78:
                resolution_met = resolution_minutes <= resolution_target and not reopened
                if resolution_met:
                    satisfaction = rng.choices((3, 4, 5), weights=(10, 35, 55), k=1)[0]
                else:
                    satisfaction = rng.choices((1, 2, 3), weights=(30, 40, 30), k=1)[0]

        rows.append(
            {
                "ticket_id": f"HD-2025-{index:04d}",
                "created_at": _iso(created_at),
                "first_response_at": _iso(first_response_at),
                "resolved_at": _iso(resolved_at),
                "priority": priority,
                "category": category,
                "channel": channel,
                "agent": agent,
                "status": status,
                "reopened": reopened,
                "satisfaction": "" if satisfaction is None else satisfaction,
            }
        )

    fieldnames = (
        "ticket_id", "created_at", "first_response_at", "resolved_at",
        "priority", "category", "channel", "agent", "status",
        "reopened", "satisfaction",
    )
    with (out / "tickets.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    closed = sum(1 for row in rows if row["status"] == "Closed")
    return {
        "tickets": len(rows),
        "closed": closed,
        "open": len(rows) - closed,
        "satisfaction_responses": sum(1 for row in rows if row["satisfaction"] != ""),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(DATA_DIR), help="Output directory")
    parser.add_argument("--tickets", type=int, default=N_TICKETS, help="Number of tickets")
    parser.add_argument("--seed", type=int, default=SEED, help="Random seed")
    args = parser.parse_args()

    counts = generate_tickets(args.out, n_tickets=args.tickets, seed=args.seed)
    print("Synthetic helpdesk dataset generated:")
    for name, value in counts.items():
        print(f"  {name:24s} {value:>4d}")
    print(f"  file                     {Path(args.out) / 'tickets.csv'}")


if __name__ == "__main__":
    main()
