"""Benchmark MCU extraction on independently specified fictional reports."""
import argparse
from collections import Counter
import json
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.mcu import extract

CASES = [
    ("Sari Demo", "Date collected 2026-05-02", "pdf", [
        ("LDL cholesterol 142 H mg/dL <100", "LDL cholesterol", "142", "mg/dL", "<100", "H"),
        ("Hemoglobin 11.2 L g/dL 12-16", "Hemoglobin", "11.2", "g/dL", "12-16", "L"),
    ]),
    ("Dedi Demo", "Tanggal pemeriksaan 2026-06-11", "png", [
        ("Glukosa puasa 95 mg/dL 70-99", "Fasting blood glucose", "95", "mg/dL", "70-99", ""),
        ("Kreatinin 0.92 mg/dL 0.7-1.3", "Creatinine", "0.92", "mg/dL", "0.7-1.3", ""),
    ]),
    ("Maya Demo", "Date collected 2026-07-20", "jpeg", [
        ("HbA1c 6.1 H % 4.0-5.6", "HbA1c", "6.1", "%", "4.0-5.6", "H"),
        ("Triglycerides 110 mg/dL <150", "Triglycerides", "110", "mg/dL", "<150", ""),
    ]),
    ("Arif Demo", "Date issued 2026-08-10", "scan-pdf", [
        ("LDL cholesterol 88 mg/dL <100", "LDL cholesterol", "88", "mg/dL", "<100", ""),
        ("ALT 24 U/L 7-56", "ALT", "24", "U/L", "7-56", ""),
    ]),
]


def score_reports(folder, manifest, output):
    fields = ("page", "label", "group", "value", "unit", "range", "flag")
    cases = json.loads(manifest.read_text(encoding="utf-8-sig"))
    if not cases or len({case["file"] for case in cases}) != len(cases):
        raise ValueError("Provide a nonempty manifest with unique report filenames.")
    totals = Counter()
    evidence = []
    for case in cases:
        path = (folder / case["file"]).resolve()
        if not path.is_relative_to(folder.resolve()):
            raise ValueError("Report must be inside the input folder.")
        expected = Counter(tuple(row[key] for key in fields) for row in case["rows"])
        try:
            actual = extract(path.read_bytes())
            error = None
        except Exception as exc:
            actual = {"rows": [], "date_evidence": [], "methods": []}
            error = type(exc).__name__
        found = Counter(tuple(row[key] for key in fields) for row in actual["rows"])
        dates_match = Counter((d["page"], d["source"]) for d in case["dates"]) == Counter(
            (d["page"], d["source"]) for d in actual["date_evidence"])
        counts = dict(expected=expected.total(), emitted=found.total(),
                      exact=(expected & found).total(), dates_matched=int(dates_match),
                      extraction_errors=int(error is not None))
        totals.update(counts)
        evidence.append(dict(file=case["file"], counts=counts, error=error,
                             missed=[dict(zip(fields, row)) for row in (expected - found).elements()],
                             extra=[dict(zip(fields, row)) for row in (found - expected).elements()],
                             expected_dates=case["dates"], extracted=actual))
    result = dict(fields=fields, reports=len(cases), totals=dict(totals),
                  exact_precision=totals["exact"] / totals["emitted"] if totals["emitted"] else None,
                  exact_recall=totals["exact"] / totals["expected"] if totals["expected"] else None,
                  cases=evidence)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "cases"}))
    return bool(totals["extraction_errors"] or totals["dates_matched"] != len(cases)
                or totals["exact"] != totals["expected"] or totals["exact"] != totals["emitted"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if any((args.reports, args.manifest, args.output)):
        if not all((args.reports, args.manifest, args.output)):
            parser.error("--reports, --manifest, and --output are required together")
        return score_reports(args.reports, args.manifest, args.output)

    evidence = []
    for name, date, fmt, rows in CASES:
        with fitz.open() as doc:
            page = doc.new_page(width=620, height=440)
            content = ["JagSi fictional laboratory report", "Patient: " + name, date,
                       "Laboratory results", *(row[0] for row in rows)]
            for index, line in enumerate(content):
                page.insert_text((42, 55 + index * 49), line, fontsize=17)
            if fmt == "pdf":
                source = doc.tobytes()
            else:
                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                if fmt == "scan-pdf":
                    with fitz.open() as scanned:
                        target = scanned.new_page(width=620, height=440)
                        target.insert_image(target.rect, pixmap=pixmap)
                        source = scanned.tobytes()
                else:
                    source = pixmap.tobytes(fmt)
        actual = extract(source)
        expected = [list(row[1:]) for row in rows]
        found = [[row[key] for key in ("label", "value", "unit", "range", "flag")] for row in actual["rows"]]
        evidence.append(dict(person=name, format=fmt, expected=expected, extracted=actual,
                             rows_match=found == expected,
                             date_match=any(d["source"] == date for d in actual["date_evidence"])))
    target = ROOT / "docs/evidence/mcu-scan-benchmark.json"
    target.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for case in evidence:
        print(case["person"], case["format"], case["rows_match"], case["date_match"])
    return any(not (case["rows_match"] and case["date_match"]) for case in evidence)


if __name__ == "__main__":
    sys.exit(main())
