"""Streamlit application for the compliance risk dashboard."""
from __future__ import annotations

from dataclasses import replace
from itertools import groupby
from operator import attrgetter

import streamlit as st

from charts import (
    compliance_gauge,
    heatmap_matrix,
    priority_bubble,
    remediation_timeline,
    sankey_figure,
    waterfall_figure,
)
from data_manager import (
    RequirementRecord,
    compute_category_scores,
    compute_overall_score,
    compute_status_counts,
    filter_records,
    load_data,
    projected_score,
)

st.set_page_config(
    page_title="Interactive Compliance Dashboard",
    layout="wide",
    page_icon="📊",
)


def _filter_controls() -> tuple[list[str], list[str], str]:
    st.markdown("### Filters")
    col1, col2, col3, col4 = st.columns([2, 1.5, 1.5, 2])

    status_options = ["Met", "Partially Meets", "Does Not Meet"]
    statuses = col1.multiselect("Status", status_options, default=status_options)

    category_options = ["CIP", "CDD"]
    category = col2.selectbox("Category", ["All", *category_options])
    categories = category_options if category == "All" else [category]

    search = col4.text_input("Search requirements", placeholder="Search by ID, section or text...")

    result_count_placeholder = col3.empty()
    return statuses, categories, search, result_count_placeholder


def _render_metrics(records: list[RequirementRecord]) -> None:
    overall = compute_overall_score(records)
    status_counts = compute_status_counts(records)
    categories = compute_category_scores(records)
    fig = compliance_gauge(overall, status_counts)
    st.plotly_chart(fig, use_container_width=True)

    met = status_counts.get("Met", 0) + status_counts.get("Partially Meets", 0) + status_counts.get("Does Not Meet", 0)
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Requirements", met)
    col2.metric("Compliance Score", f"{overall}%")
    high_priority = status_counts.get("Does Not Meet", 0)
    col3.metric("High Priority Gaps", high_priority)

    st.markdown("#### Category Scores")
    category_cols = st.columns(len(categories))
    for col, (name, score) in zip(category_cols, categories.items()):
        col.metric(name, f"{score}%")


@st.cache_data(show_spinner=False)
def _load_records() -> list[RequirementRecord]:
    return load_data()


def _page_overview(records: list[RequirementRecord]) -> None:
    _render_metrics(records)

    st.markdown("#### Requirement Heat Map")
    st.plotly_chart(heatmap_matrix(records), use_container_width=True)

    st.markdown("---")
    btn1, btn2 = st.columns(2)
    btn1.button("View Gaps")
    btn2.button("Export Report")


def _page_gap_analysis(records: list[RequirementRecord]) -> None:
    st.subheader("Score Contribution Waterfall")
    st.plotly_chart(waterfall_figure(records), use_container_width=True)

    col1, col2 = st.columns((3, 2))
    with col1:
        st.subheader("Category to Status Flow")
        st.plotly_chart(sankey_figure(records), use_container_width=True)
    with col2:
        st.subheader("Priority Matrix")
        st.plotly_chart(priority_bubble(records), use_container_width=True)

    st.subheader("Critical Gaps")
    gaps = [rec for rec in records if rec.status == "Does Not Meet"]
    if gaps:
        st.dataframe(
            {
                "ID": [rec.id for rec in gaps],
                "Section": [rec.section for rec in gaps],
                "Risk Severity": [rec.risk_severity for rec in gaps],
                "Notes": [rec.notes for rec in gaps],
            }
        )
    else:
        st.info("No critical gaps in the filtered selection.")


def _render_simulator(records: list[RequirementRecord]) -> None:
    st.markdown("#### Compliance Score Simulator")
    buttons = st.columns(3)
    gap_ids = [rec.id for rec in records if rec.status == "Does Not Meet"]
    partial_ids = [rec.id for rec in records if rec.status == "Partially Meets"]

    if buttons[0].button("Select All Gaps"):
        for rec_id in gap_ids:
            st.session_state[f"sim_{rec_id}"] = True
    if buttons[1].button("Select All Partial"):
        for rec_id in partial_ids:
            st.session_state[f"sim_{rec_id}"] = True
    if buttons[2].button("Reset"):
        for rec in records:
            st.session_state[f"sim_{rec.id}"] = False

    grouped = {
        category: list(items)
        for category, items in groupby(sorted(records, key=lambda r: (r.category, r.id)), key=attrgetter("category"))
    }

    selected_ids: list[str] = []
    for category, items in grouped.items():
        with st.expander(f"{category} Requirements", expanded=True):
            for rec in items:
                key = f"sim_{rec.id}"
                checked = st.checkbox(
                    f"{rec.id} — {rec.section} ({rec.status})",
                    key=key,
                    value=st.session_state.get(key, False),
                )
                if checked:
                    selected_ids.append(rec.id)

    projected = projected_score(records, selected_ids)
    current = compute_overall_score(records)
    delta = round(projected - current, 1)

    st.metric(
        "Projected Score",
        f"{projected}%",
        f"{delta:+.1f}%",
    )

    simulated_records = [
        replace(rec, status="Met", compliance_score=100.0) if rec.id in selected_ids else rec
        for rec in records
    ]
    st.plotly_chart(compliance_gauge(projected, compute_status_counts(simulated_records)), use_container_width=True)

    st.caption(
        f"Fixing these {len(selected_ids)} items would achieve {projected}% compliance in the selected view."
    )


def _render_requirement_details(records: list[RequirementRecord]) -> None:
    st.markdown("#### Requirement Detail List")
    for rec in records:
        with st.expander(f"{rec.id} — {rec.section}"):
            st.markdown(f"**Status:** {rec.status}")
            st.markdown(f"**Compliance Score:** {rec.compliance_score}%")
            st.markdown(f"**Requirement:** {rec.requirement}")
            st.markdown(f"**Test Steps:** {rec.test_steps}")
            if rec.notes:
                st.markdown(f"**Notes:** {rec.notes}")


def _page_remediation(records: list[RequirementRecord]) -> None:
    st.subheader("Remediation Timeline")
    st.plotly_chart(remediation_timeline(records), use_container_width=True)

    col1, col2 = st.columns((2, 3))
    with col1:
        _render_simulator(records)
    with col2:
        _render_requirement_details(records)


def main() -> None:
    all_records = _load_records()
    statuses, categories, search, result_placeholder = _filter_controls()

    filtered = filter_records(all_records, statuses=statuses, categories=categories, query=search)
    result_placeholder.metric("Results", f"{len(filtered)} of {len(all_records)}")

    page = st.radio("Navigation", ["Executive Overview", "Gap Analysis", "Remediation Planning"], horizontal=True)

    if page == "Executive Overview":
        _page_overview(filtered)
    elif page == "Gap Analysis":
        _page_gap_analysis(filtered)
    else:
        _page_remediation(filtered)


if __name__ == "__main__":
    main()
