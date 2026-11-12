from __future__ import annotations

import csv
from pathlib import Path

import generate_data as gd


def read_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_generation_writes_expected_volume(tmp_path):
    counts = gd.generate_tickets(tmp_path, n_tickets=120, seed=3)
    rows = read_rows(tmp_path / "tickets.csv")

    assert len(rows) == 120
    assert counts["tickets"] == 120
    assert counts["closed"] + counts["open"] == 120
    assert counts["closed"] > 70
    assert len({row["ticket_id"] for row in rows}) == 120


def test_generation_is_deterministic(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    gd.generate_tickets(first, n_tickets=100, seed=99)
    gd.generate_tickets(second, n_tickets=100, seed=99)

    assert (first / "tickets.csv").read_bytes() == (second / "tickets.csv").read_bytes()


def test_different_seeds_produce_different_tickets(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    gd.generate_tickets(first, n_tickets=60, seed=1)
    gd.generate_tickets(second, n_tickets=60, seed=2)

    assert (first / "tickets.csv").read_bytes() != (second / "tickets.csv").read_bytes()


def test_generated_timestamps_are_consistent(tmp_path):
    gd.generate_tickets(tmp_path, n_tickets=480, seed=7)
    rows = read_rows(tmp_path / "tickets.csv")

    created = [row["created_at"] for row in rows]
    assert created == sorted(created)

    for row in rows:
        assert row["status"] in {"Closed", "Pending", "Open"}
        assert row["priority"] in {"Low", "Medium", "High", "Critical"}
        assert row["created_at"] != ""

        if row["status"] == "Closed":
            assert row["resolved_at"] != ""
            assert row["first_response_at"] != ""
            assert row["resolved_at"] >= row["first_response_at"] >= row["created_at"]
        else:
            assert row["resolved_at"] == ""

        if row["satisfaction"]:
            assert 1 <= int(row["satisfaction"]) <= 5
