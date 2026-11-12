from __future__ import annotations

import pandas as pd
import pytest

import analyze_tickets as analysis
import generate_data as gd


def sample_tickets() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticket_id": ["T1", "T2", "T3", "T4"],
            "created_at": pd.to_datetime(
                ["2025-01-01 08:00", "2025-01-02 09:00", "2025-01-03 10:00", "2025-01-04 11:00"]
            ),
            "first_response_at": pd.to_datetime(
                ["2025-01-01 08:10", "2025-01-02 10:30", None, "2025-01-04 12:40"]
            ),
            "resolved_at": pd.to_datetime(
                ["2025-01-01 11:20", "2025-01-02 15:40", None, "2025-01-05 20:20"]
            ),
            "priority": ["Critical", "High", "Low", "Medium"],
            "category": ["Network", "Software", "Access", "Hardware"],
            "channel": ["Email", "Portal", "Chat", "Phone"],
            "agent": ["Agent A", "Agent A", "Agent B", "Agent B"],
            "status": ["Closed", "Closed", "Open", "Closed"],
            "reopened": [0, 1, 0, 0],
            "satisfaction": [5, 2, None, 3],
        }
    )


def test_enrich_tickets_applies_sla_rules():
    enriched = analysis.enrich_tickets(sample_tickets())

    assert enriched.loc[0, "response_met"]
    assert enriched.loc[0, "resolution_met"]
    assert enriched.loc[0, "sla_met"]

    assert not enriched.loc[1, "response_met"]
    assert enriched.loc[1, "resolution_met"]
    assert not enriched.loc[1, "sla_met"]

    assert not enriched.loc[2, "response_met"]
    assert pd.isna(enriched.loc[2, "resolution_met"])
    assert pd.isna(enriched.loc[2, "sla_met"])

    assert enriched.loc[3, "response_met"]
    assert not enriched.loc[3, "resolution_met"]
    assert not enriched.loc[3, "sla_met"]


def test_compute_kpis_on_known_sample():
    kpis = analysis.compute_kpis(analysis.enrich_tickets(sample_tickets()))

    assert kpis["total_tickets"] == 4
    assert kpis["closed_tickets"] == 3
    assert kpis["open_backlog"] == 1
    assert kpis["response_sla_pct"] == 50.0
    assert kpis["resolution_sla_pct"] == pytest.approx(66.7)
    assert kpis["median_resolution_hours"] == pytest.approx(6.7)
    assert kpis["reopened_rate_pct"] == pytest.approx(33.3)


def test_breakdown_partitions_tickets():
    enriched = analysis.enrich_tickets(sample_tickets())

    for dimension in ("priority", "category", "agent", "channel"):
        table = analysis.breakdown(enriched, dimension)
        assert table["tickets"].sum() == len(enriched)
        assert table["closed"].sum() == enriched["status"].eq("Closed").sum()
        assert set(table["response_sla_pct"].between(0, 100))
        resolution_values = table["resolution_sla_pct"].dropna()
        assert resolution_values.between(0, 100).all()


def test_end_to_end_analysis_writes_reports(tmp_path):
    data_dir = tmp_path / "data"
    out_dir = tmp_path / "results"
    gd.generate_tickets(data_dir, n_tickets=150, seed=13)

    result = analysis.run_analysis(data_dir / "tickets.csv", out_dir)
    kpis = result["kpis"]

    assert kpis["total_tickets"] == 150
    assert 0 < kpis["response_sla_pct"] <= 100
    assert 0 < kpis["resolution_sla_pct"] <= 100
    assert 0 <= kpis["reopened_rate_pct"] <= 100
    assert 1 <= kpis["average_csat"] <= 5

    for filename in (
        "summary.md", "summary_metrics.csv", "by_priority.csv", "by_category.csv",
        "by_agent.csv", "by_channel.csv", "monthly.csv",
    ):
        assert (out_dir / filename).exists(), filename

    for filename in (
        "sla_by_priority.png", "monthly_volume_and_sla.png",
        "resolution_time_by_priority.png", "sla_by_category.png", "agent_workload.png",
    ):
        path = out_dir / filename
        assert path.exists() and path.stat().st_size > 1000, filename

    monthly = result["tables"]["monthly"]
    assert monthly["tickets"].sum() == 150
    assert monthly["closed"].sum() == kpis["closed_tickets"]
    assert monthly["month"].is_monotonic_increasing


def test_analysis_outputs_are_reproducible(tmp_path):
    data_dir = tmp_path / "data"
    gd.generate_tickets(data_dir, n_tickets=120, seed=31)

    first = analysis.run_analysis(data_dir / "tickets.csv", tmp_path / "one", make_charts=False)
    second = analysis.run_analysis(data_dir / "tickets.csv", tmp_path / "two", make_charts=False)

    assert first["summary"] == second["summary"]
    for name in ("summary_metrics.csv", "by_priority.csv", "monthly.csv"):
        assert (tmp_path / "one" / name).read_bytes() == (tmp_path / "two" / name).read_bytes()


def test_missing_file_has_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="generate_data.py"):
        analysis.load_tickets(tmp_path / "missing.csv")
