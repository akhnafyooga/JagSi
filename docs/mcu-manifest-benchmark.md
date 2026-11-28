# MCU manifest benchmark

Run the four built-in fictional reports with `.venv/Scripts/python backend/ml/benchmark_mcu_scan.py`.

To score outside fixtures, keep reports and raw OCR output in an ignored directory such as `backend/data/mcu-eval`. Raw output can contain report text. Use fictional or authorized de-identified inputs. Write the manifest independently before running extraction.

~~~powershell
.venv/Scripts/python backend/ml/benchmark_mcu_scan.py --reports backend/data/mcu-eval --manifest backend/data/mcu-eval/expected.json --output backend/data/mcu-eval/results.json
~~~

~~~json
[
  {
    "file": "fictional.pdf",
    "rows": [
      {"page": 1, "label": "Creatinine", "group": "Kidney panel", "value": "0.92", "unit": "mg/dL", "range": "0.7-1.3", "flag": ""}
    ],
    "dates": [{"page": 1, "source": "Date collected 2026-06-11"}]
  }
]
~~~

Use empty arrays for reports with no expected rows or dates. Copy comparators into the value, such as `<0.92`. The scorer compares complete tuples including the English group, counts duplicates individually, and reports missed and extra rows. Precision and recall are null when their denominator is zero. Date lines are checked separately and exactly. A mismatch or extraction failure returns a nonzero exit status and leaves the JSON evidence available for inspection.
