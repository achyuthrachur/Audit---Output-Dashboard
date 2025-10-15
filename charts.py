"""Plotly figure helpers for the Streamlit compliance dashboard."""
from __future__ import annotations

import math
import re
from datetime import date, timedelta
from typing import List, Sequence

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from data_manager import RequirementRecord

STATUS_COLORS = {
    "Met": "#4CAF50",
    "Partially Meets": "#FFC107",
    "Does Not Meet": "#F44336",
}


def _id_sort_value(identifier: str) -> tuple[int, int, str]:
    """Sort CIP IDs before CDD IDs and use numeric order within each group."""
    normalized = identifier.upper()
    if "CIP" in normalized:
        prefix_rank = 0
    elif "CDD" in normalized:
        prefix_rank = 1
    else:
        prefix_rank = 2

    numbers = re.findall(r"(\d+)", normalized)
    number = int(numbers[-1]) if numbers else 0
    return prefix_rank, number, identifier


def compliance_gauge(overall_score: float, status_counts: dict[str, int]) -> go.Figure:
    met = status_counts.get("Met", 0)
    partial = status_counts.get("Partially Meets", 0)
    gaps = status_counts.get("Does Not Meet", 0)
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=overall_score,
            number={"suffix": "%", "font": {"size": 48}},
            title={"text": "Overall Compliance", "font": {"size": 20}},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#1E88E5"},
                "steps": [
                    {"range": [0, 60], "color": "#F44336"},
                    {"range": [60, 80], "color": "#FFC107"},
                    {"range": [80, 100], "color": "#4CAF50"},
                ],
            },
        )
    )
    fig.update_layout(
        margin=dict(t=40, b=40, l=40, r=40),
        height=350,
        annotations=[
            dict(
                x=0.5,
                y=-0.25,
                text=f"<b>{met} Met</b> - <b>{partial} Partial</b> - <b>{gaps} Gaps</b>",
                showarrow=False,
                font={"size": 16},
            )
        ],
    )
    return fig


def _grid_dimensions(count: int, columns: int) -> int:
    return math.ceil(count / columns)


def heatmap_matrix(records: Sequence[RequirementRecord], columns: int = 5) -> go.Figure:
    cip = sorted((rec for rec in records if rec.category == "CIP"), key=lambda rec: _id_sort_value(rec.id))
    cdd = sorted((rec for rec in records if rec.category == "CDD"), key=lambda rec: _id_sort_value(rec.id))

    cip_rows = _grid_dimensions(len(cip), columns)
    cdd_rows = _grid_dimensions(len(cdd), columns)
    total_rows = cip_rows + cdd_rows

    values = [[None for _ in range(columns)] for _ in range(total_rows)]
    text = [["" for _ in range(columns)] for _ in range(total_rows)]
    hover = [["" for _ in range(columns)] for _ in range(total_rows)]

    def fill(items: List[RequirementRecord], start_row: int) -> None:
        for idx, record in enumerate(items):
            row = start_row + idx // columns
            col = idx % columns
            values[row][col] = record.compliance_score
            text[row][col] = record.id
            hover[row][col] = (
                f"<b>{record.id}</b><br>{record.section}<br>Score: {record.compliance_score}%<br>Status: {record.status}"
            )

    fill(cip, 0)
    fill(cdd, cip_rows)

    color_scale = [
        [0, STATUS_COLORS["Does Not Meet"]],
        [0.5, STATUS_COLORS["Partially Meets"]],
        [1.0, STATUS_COLORS["Met"]],
    ]

    fig = go.Figure(
        data=go.Heatmap(
            z=values,
            text=text,
            texttemplate="%{text}",
            colorscale=color_scale,
            zmin=0,
            zmax=100,
            hoverinfo="text",
            hovertext=hover,
            showscale=False,
        )
    )
    fig.update_layout(
        height=360,
        margin=dict(t=40, b=40, l=40, r=40),
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        annotations=[
            dict(
                x=-0.1,
                y=1 - (cip_rows - 0.5) / total_rows if total_rows else 1,
                text="CIP Requirements",
                showarrow=False,
                xref="paper",
                yref="paper",
            ),
            dict(
                x=-0.1,
                y=(0.5) / total_rows if total_rows else 0,
                text="CDD Requirements",
                showarrow=False,
                xref="paper",
                yref="paper",
            ),
        ],
    )
    return fig


def waterfall_figure(records: Sequence[RequirementRecord]) -> go.Figure:
    if not records:
        return go.Figure()

    status_delta = {
        "Met": 0.0,
        "Partially Meets": -0.5,
        "Does Not Meet": -1.0,
    }

    sorted_records = sorted(records, key=lambda rec: _id_sort_value(rec.id))
    impacts = [
        {
            "label": record.id,
            "delta": status_delta.get(record.status, 0.0),
            "section": record.section,
            "status": record.status,
        }
        for record in sorted_records
    ]

    base_score = 0.0
    cumulative_delta = sum(item["delta"] for item in impacts)

    measure = ["absolute", *["relative" for _ in impacts], "total"]
    x_values = ["Target (0)", *[item["label"] for item in impacts], "Cumulative Gap"]
    y_values = [base_score, *[item["delta"] for item in impacts], cumulative_delta]
    text_values = [f"{base_score:.1f}", *[f"{item['delta']:+.1f}" for item in impacts], f"{cumulative_delta:.1f}"]

    customdata = [
        ("Baseline", "Target Score", f"Target: {base_score:.1f}"),
        *[(item["section"], item["status"], f"Impact: {item['delta']:+.1f}") for item in impacts],
        ("All Controls", "Cumulative", f"Gap: {cumulative_delta:.1f}"),
    ]

    fig = go.Figure(
        go.Waterfall(
            orientation="v",
            measure=measure,
            x=x_values,
            y=y_values,
            text=text_values,
            textposition="outside",
            connector={"line": {"color": "#1E88E5"}},
            customdata=customdata,
            hovertemplate=(
                "%{x}<br>Section: %{customdata[0]}<br>Status: %{customdata[1]}<br>"
                "%{customdata[2]}<extra></extra>"
            ),
            increasing={"marker": {"color": STATUS_COLORS["Met"]}},
            decreasing={"marker": {"color": STATUS_COLORS["Does Not Meet"]}},
            totals={"marker": {"color": "#90A4AE"}},
        )
    )
    fig.update_layout(
        showlegend=False,
        waterfallgap=0.2,
        margin=dict(t=40, b=80, l=40, r=40),
        xaxis=dict(tickangle=45),
        yaxis=dict(title="Cumulative Gap", tickformat="+.1f"),
    )
    return fig


def sankey_figure(records: Sequence[RequirementRecord]) -> go.Figure:
    categories = sorted({rec.category for rec in records})
    statuses = ["Met", "Partially Meets", "Does Not Meet"]

    label_map = {label: idx for idx, label in enumerate([*categories, *statuses])}
    source = []
    target = []
    values = []
    colors: List[str] = []

    for category in categories:
        cat_records = [rec for rec in records if rec.category == category]
        for status in statuses:
            count = sum(1 for rec in cat_records if rec.status == status)
            if count:
                source.append(label_map[category])
                target.append(label_map[status])
                values.append(count)
                colors.append(STATUS_COLORS[status])

    fig = go.Figure(
        go.Sankey(
            arrangement="snap",
            node=dict(
                label=[*categories, *statuses],
                pad=15,
                thickness=20,
                color="#1E88E5",
                line=dict(color="#0D47A1", width=1),
            ),
            textfont=dict(color="#FFFFFF", size=14),
            link=dict(source=source, target=target, value=values, color=colors),
        )
    )
    fig.update_layout(margin=dict(t=40, b=40, l=40, r=40))
    return fig


def priority_bubble(records: Sequence[RequirementRecord]) -> go.Figure:
    ordered = sorted(
        records,
        key=lambda rec: (-rec.risk_severity, _id_sort_value(rec.id)),
    )
    x_positions = list(range(1, len(ordered) + 1))
    colors = [STATUS_COLORS.get(record.status, "#1E88E5") for record in ordered]
    customdata = [
        (record.id, record.risk_severity, record.status, record.section) for record in ordered
    ]

    fig = go.Figure(
        data=go.Scatter(
            x=x_positions,
            y=[record.risk_severity for record in ordered],
            mode="markers",
            marker=dict(
                size=28,
                color=colors,
                opacity=0.85,
                line=dict(color="#1F1F1F", width=1),
            ),
            customdata=customdata,
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Risk Severity: %{customdata[1]:.1f}<br>"
                "Status: %{customdata[2]}<br>"
                "Section: %{customdata[3]}<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        xaxis=dict(
            title="Implementation Difficulty Index",
            tickmode="linear",
            dtick=1,
            range=[0, len(ordered) + 1],
        ),
        yaxis=dict(title="Risk Severity", range=[0, 100]),
        margin=dict(t=40, b=40, l=40, r=40),
        showlegend=False,
    )
    return fig


def remediation_timeline(records: Sequence[RequirementRecord]) -> go.Figure:
    start_date = date(2025, 10, 1)
    bars = []
    for idx, record in enumerate(records):
        if record.status == "Does Not Meet":
            duration = 90
        elif record.status == "Partially Meets":
            duration = 45
        else:
            duration = 30
        start = start_date + timedelta(days=15 * idx)
        finish = start + timedelta(days=duration)
        bars.append((record, start, finish))

    fig = make_subplots(rows=1, cols=1)
    for record, start, finish in bars:
        fig.add_trace(
            go.Bar(
                x=[(finish - start).days],
                y=[record.id],
                base=start,
                orientation="h",
                marker_color=STATUS_COLORS.get(record.status, "#1E88E5"),
                hovertemplate=(
                    f"<b>{record.id}</b><br>{record.section}<br>Status: {record.status}<br>Start: {start}<br>End: {finish}<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        barmode="overlay",
        xaxis=dict(title="Timeline"),
        yaxis=dict(title="Requirement", autorange="reversed"),
        height=600,
        margin=dict(t=40, b=40, l=40, r=40),
        showlegend=False,
    )
    return fig
