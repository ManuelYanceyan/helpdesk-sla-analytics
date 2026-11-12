"""Analyse synthetic IT helpdesk tickets and export SLA reports and charts."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "tickets.csv"
RESULTS_DIR = BASE_DIR / "results"

PRIORITIES = ("Low", "Medium", "High", "Critical")
RESPONSE_TARGET_MIN = {"Low": 480, "Medium": 240, "High": 60, "Critical": 15}
RESOLUTION_TARGET_MIN = {"Low": 2880, "Medium": 1440, "High": 480, "Critical": 240}

DATE_COLUMNS = ("created_at", "first_response_at", "resolved_at")
REQUIRED_COLUMNS = (
    "ticket_id", "created_at", "first_response_at", "resolved_at",
    "priority", "category", "channel", "agent", "status",
    "reopened", "satisfaction",
)

KPI_LABELS = {
    "total_tickets": "Total tickets",
    "closed_tickets": "Closed tickets",
    "open_backlog": "Open / pending backlog",
    "critical_backlog": "Critical backlog",
    "response_sla_pct": "First-response SLA (%)",
    "resolution_sla_pct": "Resolution SLA (%)",
    "avg_first_response_minutes": "Average first response (minutes)",
    "median_resolution_hours": "Median resolution (hours)",
    "reopened_rate_pct": "Reopened rate among closed (%)",
    "average_csat": "Average CSAT (1-5)",
    "csat_responses": "CSAT responses",
    "resolved_tickets": "Resolved tickets",
}
SLA_REFERENCE_PCT = 90.0


def load_tickets(path: Path | str = DATA_FILE) -> pd.DataFrame:
    """Load and validate the synthetic ticket CSV."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Ticket file not found: {path}. Run `python generate_data.py` first."
        )

    tickets = pd.read_csv(path)
    missing = [column for column in REQUIRED_COLUMNS if column not in tickets.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    for column in DATE_COLUMNS:
        tickets[column] = pd.to_datetime(tickets[column], errors="coerce")

    if tickets["created_at"].isna().any():
        raise ValueError("created_at contains empty or invalid timestamps")

    unknown_priorities = set(tickets["priority"].dropna()) - set(PRIORITIES)
    if unknown_priorities:
        raise ValueError(f"Unknown priorities: {sorted(unknown_priorities)}")

    tickets["reopened"] = pd.to_numeric(tickets["reopened"], errors="coerce").fillna(0).astype(int)
    tickets["satisfaction"] = pd.to_numeric(tickets["satisfaction"], errors="coerce")
    return tickets


def enrich_tickets(tickets: pd.DataFrame) -> pd.DataFrame:
    """Add durations, SLA flags and reporting columns."""
    enriched = tickets.copy()

    for column in DATE_COLUMNS:
        enriched[column] = pd.to_datetime(enriched[column], errors="coerce")

    enriched["response_minutes"] = (
        enriched["first_response_at"] - enriched["created_at"]
    ).dt.total_seconds() / 60
    enriched["resolution_minutes"] = (
        enriched["resolved_at"] - enriched["created_at"]
    ).dt.total_seconds() / 60

    enriched["response_target_minutes"] = enriched["priority"].astype(str).map(
        RESPONSE_TARGET_MIN
    )
    enriched["resolution_target_minutes"] = enriched["priority"].astype(str).map(
        RESOLUTION_TARGET_MIN
    )

    # A missing first response is treated as a breach because the target has
    # already elapsed for every ticket in this 2025 dataset.
    enriched["response_met"] = (
        enriched["response_minutes"] <= enriched["response_target_minutes"]
    ).fillna(False).astype(bool)

    resolved_mask = (
        enriched["resolved_at"].notna() & enriched["resolution_minutes"].notna()
    )
    resolution_met = pd.Series(pd.NA, index=enriched.index, dtype="boolean")
    resolution_met.loc[resolved_mask] = (
        enriched.loc[resolved_mask, "resolution_minutes"]
        <= enriched.loc[resolved_mask, "resolution_target_minutes"]
    )
    enriched["resolution_met"] = resolution_met

    sla_met = pd.Series(pd.NA, index=enriched.index, dtype="boolean")
    sla_met.loc[resolved_mask] = (
        enriched.loc[resolved_mask, "response_met"]
        & resolution_met.loc[resolved_mask].astype(bool)
    )
    enriched["sla_met"] = sla_met

    enriched["resolution_hours"] = enriched["resolution_minutes"] / 60
    enriched["month"] = enriched["created_at"].dt.strftime("%Y-%m")
    enriched["is_closed"] = enriched["status"].eq("Closed")
    return enriched


def _resolution_sla(enriched: pd.DataFrame) -> float | None:
    values = enriched.loc[enriched["resolved_at"].notna(), "resolution_met"]
    if values.empty:
        return None
    return float(100.0 * values.astype(bool).mean())


def compute_kpis(enriched: pd.DataFrame) -> dict:
    """Return headline service-desk metrics."""
    resolved_mask = enriched["resolved_at"].notna()
    closed_mask = enriched["status"].eq("Closed")
    csat = enriched["satisfaction"].dropna()
    critical_backlog = (
        ~closed_mask & enriched["priority"].astype(str).eq("Critical")
    ).sum()

    return {
        "total_tickets": int(len(enriched)),
        "closed_tickets": int(closed_mask.sum()),
        "open_backlog": int((~closed_mask).sum()),
        "critical_backlog": int(critical_backlog),
        "response_sla_pct": round(100.0 * enriched["response_met"].mean(), 1),
        "resolution_sla_pct": round(float(_resolution_sla(enriched)), 1),
        "avg_first_response_minutes": round(float(enriched["response_minutes"].mean()), 1),
        "median_resolution_hours": round(float(enriched["resolution_hours"].median()), 1),
        "reopened_rate_pct": round(100.0 * enriched.loc[closed_mask, "reopened"].mean(), 1),
        "average_csat": round(float(csat.mean()), 2),
        "csat_responses": int(csat.notna().sum()),
        "resolved_tickets": int(resolved_mask.sum()),
    }


def breakdown(enriched: pd.DataFrame, dimension: str) -> pd.DataFrame:
    """Aggregate SLA, backlog and CSAT by a ticket dimension."""
    if dimension == "priority":
        groups = [
            (priority, enriched[enriched["priority"].astype(str) == priority])
            for priority in PRIORITIES
        ]
    else:
        grouped = enriched.groupby(dimension, observed=True, dropna=False)
        groups = sorted(grouped, key=lambda item: (-len(item[1]), str(item[0])))

    rows = []
    for key, group in groups:
        if group.empty:
            continue

        resolved = group.loc[group["resolved_at"].notna()]
        resolution_sla = _resolution_sla(group)
        avg_resolution = (
            round(float(resolved["resolution_hours"].mean()), 1)
            if not resolved.empty else None
        )
        csat_values = group["satisfaction"].dropna()

        rows.append(
            {
                "group": str(key),
                "tickets": int(len(group)),
                "closed": int(group["status"].eq("Closed").sum()),
                "backlog": int((~group["status"].eq("Closed")).sum()),
                "response_sla_pct": round(100.0 * group["response_met"].mean(), 1),
                "resolution_sla_pct": None if resolution_sla is None else round(resolution_sla, 1),
                "avg_resolution_hours": avg_resolution,
                "avg_csat": None if csat_values.empty else round(float(csat_values.mean()), 2),
            }
        )

    return pd.DataFrame(rows)


def monthly_trend(enriched: pd.DataFrame) -> pd.DataFrame:
    """Build a month-by-month volume and SLA table."""
    rows = []
    for month, group in enriched.groupby("month", sort=True):
        resolved = group.loc[group["resolved_at"].notna()]
        resolution_met = resolved["resolution_met"].astype(bool)
        rows.append(
            {
                "month": str(month),
                "tickets": int(len(group)),
                "closed": int(group["status"].eq("Closed").sum()),
                "response_breaches": int((~group["response_met"]).sum()),
                "resolution_breaches": int((~resolution_met).sum()),
                "response_sla_pct": round(100.0 * group["response_met"].mean(), 1),
                "resolution_sla_pct": (
                    round(100.0 * resolution_met.mean(), 1) if len(resolved) else None
                ),
                "avg_csat": (
                    round(float(group["satisfaction"].dropna().mean()), 2)
                    if group["satisfaction"].notna().any() else None
                ),
            }
        )
    return pd.DataFrame(rows)


def _format(value) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    if isinstance(value, float):
        if value.is_integer():
            return f"{int(value):,}"
        return f"{value:,.2f}"
    return str(value)


def markdown_table(frame: pd.DataFrame) -> str:
    columns = list(frame.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(_format(row[column]) for column in columns) + " |")
    return "\n".join(lines)


def build_summary(
    kpis: dict,
    by_priority: pd.DataFrame,
    by_category: pd.DataFrame,
    by_agent: pd.DataFrame,
    monthly: pd.DataFrame,
) -> str:
    kpi_table = pd.DataFrame(
        [
            (KPI_LABELS.get(key, key.replace("_", " ").capitalize()), value)
            for key, value in kpis.items()
        ],
        columns=["Metric", "Observed value"],
    )
    priority_table = by_priority[
        ["group", "tickets", "response_sla_pct", "resolution_sla_pct", "avg_resolution_hours"]
    ].rename(columns={"group": "priority"})
    category_table = by_category[
        ["group", "tickets", "response_sla_pct", "resolution_sla_pct", "avg_csat"]
    ].rename(columns={"group": "category"})
    agent_table = by_agent.head(5)[
        ["group", "tickets", "closed", "resolution_sla_pct", "avg_csat"]
    ].rename(columns={"group": "agent"})

    worst_category = by_category[
        (by_category["tickets"] >= 30)
    ].dropna(subset=["resolution_sla_pct"]).sort_values(
        "resolution_sla_pct"
    ).iloc[0]

    return "\n".join(
        [
            "# IT Helpdesk SLA Analytics - Observed Results",
            "",
            "> Synthetic demonstration data for 2025. Not a client engagement or production service desk.",
            "",
            "## Headline metrics",
            "",
            markdown_table(kpi_table),
            "",
            "## SLA by priority",
            "",
            markdown_table(priority_table),
            "",
            "## SLA by category",
            "",
            markdown_table(category_table),
            "",
            "## Top five agents by ticket volume",
            "",
            markdown_table(agent_table),
            "",
            "## Last six months",
            "",
            markdown_table(monthly.tail(6)),
            "",
            "## Reading notes",
            "",
            f"- The lowest resolution-SLA category with at least 30 tickets is "
            f"{worst_category['group']} at {worst_category['resolution_sla_pct']:.1f}%.",
            "- First-response SLA is measured on all tickets; an unanswered open ticket counts as a breach.",
            "- Resolution SLA is measured only on tickets with a resolution timestamp.",
            "- CSAT is the mean of available 1-5 satisfaction responses, not a percentage.",
            "- Durations use 24/7 calendar time, not business hours.",
            "- The 90% line in the charts is a visual reference for this demo, not a contractual target.",
        ]
    ) + "\n"


def _bar_labels(ax, bars, suffix="%"):
    for bar in bars:
        height = bar.get_height()
        ax.annotate(
            f"{height:.0f}{suffix}",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
        )


def chart_sla_by_priority(by_priority: pd.DataFrame, path: Path) -> None:
    frame = by_priority.copy()
    positions = list(range(len(frame)))
    width = 0.38
    response = pd.to_numeric(frame["response_sla_pct"], errors="coerce").fillna(0)
    resolution = pd.to_numeric(frame["resolution_sla_pct"], errors="coerce").fillna(0)

    fig, ax = plt.subplots(figsize=(8, 4.6))
    first = ax.bar([x - width / 2 for x in positions], response, width, label="First response", color="#2a6f97")
    second = ax.bar([x + width / 2 for x in positions], resolution, width, label="Resolution", color="#f4a261")
    _bar_labels(ax, first)
    _bar_labels(ax, second)

    ax.axhline(SLA_REFERENCE_PCT, color="#6c757d", linestyle="--", linewidth=1, label="Demo reference (90%)")
    ax.set_xticks(positions, frame["group"])
    ax.set_ylim(0, 110)
    ax.set_ylabel("SLA compliance (%)")
    ax.set_title("SLA compliance by priority (synthetic data)")
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def chart_monthly(monthly: pd.DataFrame, path: Path) -> None:
    fig, ax1 = plt.subplots(figsize=(9, 4.8))
    ax1.bar(monthly["month"], monthly["tickets"], color="#b7c9d6", label="Tickets created")
    ax1.set_ylabel("Tickets created")
    ax1.tick_params(axis="x", rotation=45)
    ax1.set_ylim(0, max(monthly["tickets"].max() * 1.35, 10))

    ax2 = ax1.twinx()
    ax2.plot(monthly["month"], monthly["response_sla_pct"], marker="o", color="#2a6f97", linewidth=1.7, label="First-response SLA")
    ax2.plot(monthly["month"], monthly["resolution_sla_pct"], marker="s", color="#e76f51", linewidth=1.7, label="Resolution SLA")
    ax2.axhline(SLA_REFERENCE_PCT, color="#6c757d", linestyle="--", linewidth=1)
    ax2.set_ylim(0, 110)
    ax2.set_ylabel("SLA compliance (%)")

    handles1, labels1 = ax1.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    fig.legend(handles1 + handles2, labels1 + labels2, loc="upper center", ncol=3, fontsize=8, frameon=False)
    ax1.set_title("Monthly volume and SLA compliance (synthetic data)", pad=28)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def chart_resolution_box(enriched: pd.DataFrame, path: Path) -> None:
    groups = []
    labels = []
    for priority in PRIORITIES:
        values = enriched.loc[
            enriched["priority"].astype(str).eq(priority), "resolution_hours"
        ].dropna()
        values = values[values > 0]
        if not values.empty:
            groups.append(values.to_numpy())
            labels.append(priority)

    fig, ax = plt.subplots(figsize=(8, 4.6))
    if groups:
        box = ax.boxplot(groups, tick_labels=labels, patch_artist=True, widths=0.55)
        for patch in box["boxes"]:
            patch.set_facecolor("#a8dadc")
            patch.set_edgecolor("#1d3557")
        ax.set_yscale("log")
        ax.set_ylabel("Resolution time (hours, log scale)")
    else:
        ax.text(0.5, 0.5, "No resolved tickets", ha="center", va="center")
    ax.set_title("Resolution-time distribution by priority (synthetic data)")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def chart_category(by_category: pd.DataFrame, path: Path) -> None:
    frame = by_category.dropna(subset=["resolution_sla_pct"]).sort_values(
        "resolution_sla_pct"
    )
    positions = list(range(len(frame)))
    height = 0.38
    response = pd.to_numeric(frame["response_sla_pct"], errors="coerce").fillna(0)
    resolution = pd.to_numeric(frame["resolution_sla_pct"], errors="coerce").fillna(0)

    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.barh([y + height / 2 for y in positions], response, height, label="First response", color="#457b9d")
    ax.barh([y - height / 2 for y in positions], resolution, height, label="Resolution", color="#e9c46a")
    ax.axvline(SLA_REFERENCE_PCT, color="#6c757d", linestyle="--", linewidth=1, label="Demo reference (90%)")
    ax.set_yticks(positions, frame["group"])
    ax.set_xlim(0, 110)
    ax.set_xlabel("SLA compliance (%)")
    ax.set_title("SLA compliance by category (synthetic data)")
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def chart_agent_workload(by_agent: pd.DataFrame, path: Path) -> None:
    frame = by_agent.head(8).sort_values("tickets")
    fig, ax = plt.subplots(figsize=(8, 4.6))
    ax.barh(frame["group"], frame["closed"], color="#2a9d8f", label="Closed")
    ax.barh(frame["group"], frame["backlog"], left=frame["closed"], color="#e76f51", label="Open / pending")
    ax.set_xlabel("Tickets")
    ax.set_title("Agent workload (synthetic data)")
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def save_charts(enriched: pd.DataFrame, tables: dict[str, pd.DataFrame], out_dir: Path) -> list[Path]:
    paths = [
        out_dir / "sla_by_priority.png",
        out_dir / "monthly_volume_and_sla.png",
        out_dir / "resolution_time_by_priority.png",
        out_dir / "sla_by_category.png",
        out_dir / "agent_workload.png",
    ]
    chart_sla_by_priority(tables["by_priority"], paths[0])
    chart_monthly(tables["monthly"], paths[1])
    chart_resolution_box(enriched, paths[2])
    chart_category(tables["by_category"], paths[3])
    chart_agent_workload(tables["by_agent"], paths[4])
    return paths


def run_analysis(
    data_path: Path | str = DATA_FILE,
    out_dir: Path | str = RESULTS_DIR,
    make_charts: bool = True,
) -> dict:
    """Load, enrich, aggregate and export the helpdesk analysis."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    enriched = enrich_tickets(load_tickets(data_path))
    kpis = compute_kpis(enriched)
    tables = {
        "by_priority": breakdown(enriched, "priority"),
        "by_category": breakdown(enriched, "category"),
        "by_agent": breakdown(enriched, "agent"),
        "by_channel": breakdown(enriched, "channel"),
        "monthly": monthly_trend(enriched),
    }

    pd.DataFrame(
        list(kpis.items()), columns=["metric", "value"]
    ).to_csv(out_dir / "summary_metrics.csv", index=False)
    for name, frame in tables.items():
        frame.to_csv(out_dir / f"{name}.csv", index=False)

    summary = build_summary(
        kpis,
        tables["by_priority"],
        tables["by_category"],
        tables["by_agent"],
        tables["monthly"],
    )
    (out_dir / "summary.md").write_text(summary, encoding="utf-8")

    charts = save_charts(enriched, tables, out_dir) if make_charts else []

    return {
        "tickets": enriched,
        "kpis": kpis,
        "tables": tables,
        "summary": summary,
        "charts": charts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default=str(DATA_FILE), help="Ticket CSV path")
    parser.add_argument("--out", default=str(RESULTS_DIR), help="Results directory")
    parser.add_argument("--no-charts", action="store_true", help="Skip PNG chart generation")
    args = parser.parse_args()

    result = run_analysis(args.data, args.out, make_charts=not args.no_charts)
    print(result["summary"])
    print(f"Wrote reports to {args.out}")


if __name__ == "__main__":
    main()
