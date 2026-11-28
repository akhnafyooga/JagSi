"""Build developer-authored MCU fixtures for debugging, with fixed expected rows."""
import json
from io import BytesIO
from pathlib import Path

import fitz
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
folder = ROOT / "backend/data/mcu-development"
folder.mkdir(parents=True, exist_ok=True)

manifest = []
for case in ("rotated", "blurred", "decimal-comma", "missing-unit", "two-dates"):
    value = "0,92" if case == "decimal-comma" else "0.92"
    unit = "" if case == "missing-unit" else "mg/dL"
    dates = ["Date collected 2026-06-11"]
    if case == "two-dates":
        dates.append("Date issued 2026-06-12")
    with fitz.open() as doc:
        page = doc.new_page(width=620, height=440)
        for i, line in enumerate(["JagSi fictional laboratory report", "Patient: Demo Patient",
                                  *dates, "Laboratory results",
                                  f"Creatinine {value} {unit} 0.7-1.3"]):
            page.insert_text((42, 55 + i * 49), line, fontsize=17)
        if case in ("rotated", "blurred"):
            filename = case + ".png"
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            with Image.open(BytesIO(pixmap.tobytes("png"))) as image:
                transformed = (image.rotate(90, expand=True) if case == "rotated"
                               else image.filter(ImageFilter.GaussianBlur(2.7)))
                transformed.save(folder / filename)
        else:
            filename = case + ".pdf"
            (folder / filename).write_bytes(doc.tobytes())
    manifest.append(dict(file=filename, rows=[
        dict(page=1, label="Creatinine", group="Kidney panel", value=value,
             unit=unit, range="0.7-1.3", flag="")],
        dates=[dict(page=1, source=date) for date in dates]))
(folder / "expected.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
