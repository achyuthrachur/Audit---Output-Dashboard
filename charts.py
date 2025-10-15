"""Plotly figure helpers for the Streamlit compliance dashboard."""
from __future__ import annotations

import math
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
                text=f"<b>{met} Met</b> • <b>{partial} Partial</b> • <b>{gaps} Gaps</b>",
                showarrow=False,
                font={"size": 16},
            )
        ],
    )
    return fig


def _grid_dimensions(count: int, columns: int) -> int:
    return math.ceil(count / columns)


def heatmap_matrix(records: Sequence[RequirementRecord], columns: int = 5) -> go.Figure:
    cip = sorted((rec for rec in records if rec.category == "CIP"), key=lambda rec: rec.id)
    cdd = sorted((rec for rec in records if rec.category == "CDD"), key=lambda rec: rec.id)
    cip = [rec for rec in records if rec.category == "CIP"]
    cdd = [rec for rec in records if rec.category == "CDD"]

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
    y_labels = [
        *("CIP" for _ in range(cip_rows)),
        *("CDD" for _ in range(cdd_rows)),
    ]
    fig.update_layout(
        height=360,
        margin=dict(t=40, b=40, l=40, r=40),
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        annotations=[
            dict(x=-0.1, y=1 - (cip_rows - 0.5) / total_rows, text="CIP Requirements", showarrow=False, xref="paper", yref="paper"),
            dict(x=-0.1, y=(0.5) / total_rows, text="CDD Requirements", showarrow=False, xref="paper", yref="paper"),
        ],
    )
    return fig


def waterfall_figure(records: Sequence[RequirementRecord]) -> go.Figure:
    impacts = []
    for record in records:
        if record.status == "Met":
            delta = 0.0
        elif record.status == "Partially Meets":
            delta = -0.5
        else:
            delta = -1.0
        impacts.append(
            {
                "label": record.id,
                "delta": delta,
                "section": record.section,
                "status": record.status,
            }
        )

    total_gap = round(sum(item["delta"] for item in impacts), 2)
    measure = ["relative" for _ in impacts]
    text = [f"{item['delta']:+.1f}" for item in impacts]
    marker_colors = [
        "#90A4AE",
        *[STATUS_COLORS.get(item["status"], "#1E88E5") for item in impacts],
        "#1E88E5",
    ]
            delta = 0
        elif record.status == "Partially Meets":
            delta = -50
        else:
            delta = -100
        impacts.append({"label": record.id, "delta": delta, "section": record.section, "status": record.status})

    base = 100
    measure = ["relative" for _ in impacts]
    text = [f"{item['delta']}" for item in impacts]

    fig = go.Figure(
        go.Waterfall(
            orientation="v",
            measure=["absolute", *measure, "total"],
            x=["Target Score", *[item["label"] for item in impacts], "Total Gap"],
            textposition="outside",
            text=["0", *text, f"{total_gap:+.1f}"],
            y=[0.0, *[item["delta"] for item in impacts], total_gap],
            marker={"color": marker_colors},
            connector={"line": {"color": "#1E88E5"}},
            customdata=[
                ("Baseline", "Target"),
                *[(item["section"], item["status"]) for item in impacts],
                ("All Controls", "Cumulative"),
            ],
            hovertemplate=(
                "%{x}<br>Section: %{customdata[0]}<br>Status: %{customdata[1]}<br>Contribution: %{y:+.1f}<extra></extra>"
            ),
            x=["Potential Score", *[item["label"] for item in impacts], "Actual Score"],
            textposition="outside",
            text=["", *text, ""],
            y=[base, *[item["delta"] for item in impacts], 0],
            connector={"line": {"color": "#1E88E5"}},
        )
    )
    fig.update_layout(
        showlegend=False,
        waterfallgap=0.2,
        margin=dict(t=40, b=80, l=40, r=40),
        xaxis=dict(tickangle=45),
        yaxis=dict(title="Gap Contribution", tickformat="+.1f"),
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
            node=dict(label=[*categories, *statuses], pad=15, thickness=20, color="#1E88E5"),
            link=dict(source=source, target=target, value=values, color=colors),
        )
    )
    fig.update_layout(margin=dict(t=40, b=40, l=40, r=40))
    return fig


def priority_bubble(records: Sequence[RequirementRecord]) -> go.Figure:
    scatter_x = []
    scatter_y = []
    text = []
    colors = []

    for idx, record in enumerate(records):
        difficulty = 1 + (idx % 10)
        scatter_x.append(difficulty)
        scatter_y.append(record.risk_severity)
        text.append(record.id)
        colors.append(STATUS_COLORS.get(record.status, "#1E88E5"))

    fig = go.Figure(
        data=go.Scatter(
            x=scatter_x,
            y=scatter_y,
            text=text,
            mode="markers+text",
            marker=dict(size=30, color=colors, opacity=0.8),
            textposition="middle center",
        )
    )
    fig.update_layout(
        xaxis=dict(title="Implementation Difficulty", range=[0, 11]),
        yaxis=dict(title="Risk Severity", range=[0, 100]),
        margin=dict(t=40, b=40, l=40, r=40),
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
