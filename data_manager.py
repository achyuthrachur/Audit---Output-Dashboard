"""Data layer for the Streamlit compliance dashboard."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from statistics import mean
from typing import Dict, Iterable, List, Optional, Sequence

DATA_PATH = Path(__file__).resolve().parent / "data" / "compliance_dashboard_data.csv"

SCORE_BY_STATUS = {
    "Met": 100,
    "Partially Meets": 50,
    "Does Not Meet": 0,
}


@dataclass(frozen=True)
class RequirementRecord:
    id: str
    section: str
    category: str
    status: str
    compliance_score: float
    requirement: str
    test_steps: str
    notes: str

    @property
    def risk_severity(self) -> float:
        return 100 - self.compliance_score


def _read_rows(path: Path) -> List[RequirementRecord]:
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        records = [
            RequirementRecord(
                id=row["ID"].strip(),
                section=row["Section"].strip(),
                category=row["Main Category"].strip(),
                status=row["Status"].strip(),
                compliance_score=float(row["Compliance Score"]),
                requirement=row["Requirement"].strip(),
                test_steps=row["Test Steps"].strip(),
                notes=row["Notes"].strip(),
            )
            for row in reader
            if row.get("ID")
        ]
    return records


@lru_cache(maxsize=1)
def load_data() -> List[RequirementRecord]:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            "Expected data file missing. Run scripts/convert_excel_to_csv.py first."
        )
    return _read_rows(DATA_PATH)


def compute_overall_score(records: Optional[Sequence[RequirementRecord]] = None) -> float:
    dataset = records if records is not None else load_data()
    if not dataset:
        return 0.0
    return round(mean(rec.compliance_score for rec in dataset), 1)


def compute_category_scores(records: Optional[Sequence[RequirementRecord]] = None) -> Dict[str, float]:
    dataset = records if records is not None else load_data()
    grouped: Dict[str, List[float]] = {}
    for rec in dataset:
        grouped.setdefault(rec.category, []).append(rec.compliance_score)
    return {category: round(mean(scores), 1) for category, scores in grouped.items()}


def compute_status_counts(records: Optional[Sequence[RequirementRecord]] = None) -> Dict[str, int]:
    dataset = records if records is not None else load_data()
    counts = {"Met": 0, "Partially Meets": 0, "Does Not Meet": 0}
    for rec in dataset:
        counts[rec.status] = counts.get(rec.status, 0) + 1
    return counts


def filter_records(
    records: Sequence[RequirementRecord],
    statuses: Optional[Iterable[str]] = None,
    categories: Optional[Iterable[str]] = None,
    query: Optional[str] = None,
) -> List[RequirementRecord]:
    statuses_set = {status.lower() for status in statuses or [] if status}
    categories_set = {category.lower() for category in categories or [] if category}
    normalized_query = query.lower().strip() if query else ""

    filtered: List[RequirementRecord] = []
    for record in records:
        if statuses_set and record.status.lower() not in statuses_set:
            continue
        if categories_set and record.category.lower() not in categories_set:
            continue
        if normalized_query:
            haystack = " ".join(
                [record.id, record.section, record.requirement, record.notes]
            ).lower()
            if normalized_query not in haystack:
                continue
        filtered.append(record)
    return filtered


def projected_score(records: Sequence[RequirementRecord], selected_ids: Iterable[str]) -> float:
    selected = {req_id.lower() for req_id in selected_ids}
    simulated_scores: List[float] = []
    for record in records:
        if record.id.lower() in selected:
            simulated_scores.append(SCORE_BY_STATUS["Met"])
        else:
            simulated_scores.append(record.compliance_score)
    return round(mean(simulated_scores), 1) if simulated_scores else 0.0


def requirements_by_status(records: Sequence[RequirementRecord]) -> Dict[str, List[RequirementRecord]]:
    grouped: Dict[str, List[RequirementRecord]] = {"Met": [], "Partially Meets": [], "Does Not Meet": []}
    for record in records:
        grouped.setdefault(record.status, []).append(record)
    return grouped


def get_requirement(record_id: str) -> Optional[RequirementRecord]:
    for record in load_data():
        if record.id == record_id:
            return record
    return None
