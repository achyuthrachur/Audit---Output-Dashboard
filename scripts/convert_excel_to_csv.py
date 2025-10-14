"""Utility to convert the provided Excel questionnaire into a CSV used by the app."""
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Iterable, List
from xml.etree import ElementTree
from zipfile import ZipFile

SOURCE_FILE = Path(__file__).resolve().parent.parent / "CIP CDD Compliance Questionnaire - FILLED (REFERENCE) (1).xlsx"
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "data" / "compliance_dashboard_data.csv"

STATUS_SCORES = {
    "Met": 100,
    "Partially Meets": 50,
    "Does Not Meet": 0,
}


def _load_shared_strings(zf: ZipFile) -> List[str]:
    """Return the list of shared strings stored in the workbook."""
    shared_path = "xl/sharedStrings.xml"
    if shared_path not in zf.namelist():
        return []

    root = ElementTree.fromstring(zf.read(shared_path))
    strings: List[str] = []
    for si in root:
        text_parts = [node.text or "" for node in si.iter() if node.tag.endswith("}t")]
        strings.append("".join(text_parts))
    return strings


def _iter_sheet_rows(zf: ZipFile, sheet_name: str, shared_strings: List[str]) -> Iterable[List[str]]:
    ns = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    root = ElementTree.fromstring(zf.read(sheet_name))

    for row in root.findall(".//main:row", ns):
        values: List[str] = []
        for cell in row.findall("main:c", ns):
            cell_type = cell.get("t")
            value_node = cell.find("main:v", ns)
            if value_node is None:
                values.append("")
                continue

            value = value_node.text or ""
            if cell_type == "s" and value:
                value = shared_strings[int(value)]
            values.append(value)
        if values:
            yield values


def _detect_status(row: List[str]) -> str:
    status_columns = {
        "Met": 8,
        "Partially Meets": 9,
        "Does Not Meet": 10,
    }
    for label, index in status_columns.items():
        if index < len(row) and row[index] and row[index] != "0":
            return label
    return "Partially Meets"


def main() -> None:
    with ZipFile(SOURCE_FILE) as zf:
        shared_strings = _load_shared_strings(zf)
        sheet_name = "xl/worksheets/sheet1.xml"
        rows = list(_iter_sheet_rows(zf, sheet_name, shared_strings))

    id_pattern = re.compile(r"COMPL-[A-Z]+-\d+")

    processed = []
    for row in rows:
        if not row or not id_pattern.match(row[0]):
            continue
        requirement_id = row[0]
        section = row[1] if len(row) > 1 else ""
        requirement_text = row[3] if len(row) > 3 else ""
        test_steps = row[7] if len(row) > 7 else ""
        notes = row[11] if len(row) > 11 else ""
        status = _detect_status(row)
        category = "CIP" if "-CIP-" in requirement_id else "CDD"
        score = STATUS_SCORES[status]

        processed.append(
            {
                "ID": requirement_id,
                "Section": section,
                "Main Category": category,
                "Status": status,
                "Compliance Score": score,
                "Requirement": requirement_text,
                "Test Steps": test_steps,
                "Notes": notes,
            }
        )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "ID",
                "Section",
                "Main Category",
                "Status",
                "Compliance Score",
                "Requirement",
                "Test Steps",
                "Notes",
            ],
        )
        writer.writeheader()
        writer.writerows(processed)

    print(f"Wrote {len(processed)} rows to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
