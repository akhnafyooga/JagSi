"""Local MCU extraction. Candidate rows retain their source line for review."""
import os
import re
from functools import lru_cache

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()
LIMIT = 15 * 1024 * 1024
# Keep specific labels first so glucose variants retain their context.
TESTS = (
    (r"glukosa puasa|gula darah puasa|fasting glucose", "Blood glucose", "Fasting blood glucose"),
    (r"glukosa sewaktu|gula darah sewaktu|random glucose", "Blood glucose", "Random blood glucose"),
    (r"glucose,? serum|glukosa|glucose", "Blood glucose", "Serum glucose"),
    (r"hemoglobin a1c|hba1c", "Blood glucose", "HbA1c"),
    (r"hemoglobin|haemoglobin", "Complete blood count", "Hemoglobin"),
    (r"wbc|leukosit", "Complete blood count", "White blood cell count"),
    (r"platelets|trombosit", "Complete blood count", "Platelet count"),
    (r"cholesterol,? total|kolesterol total|total cholesterol", "Lipid profile", "Total cholesterol"),
    (r"hdl cholesterol|kolesterol hdl|hdl", "Lipid profile", "HDL cholesterol"),
    (r"ldl cholesterol(?: \(calculated\)| calc)?|kolesterol ldl|ldl", "Lipid profile", "LDL cholesterol"),
    (r"triglycerides|trigliserida", "Lipid profile", "Triglycerides"),
    (r"creatinine,? serum|kreatinin|creatinine", "Kidney panel", "Creatinine"),
    (r"bun|ureum|urea", "Kidney panel", "Urea / BUN (see source)"),
    (r"ast\s*\(sgot\)|sgot|ast", "Liver panel", "AST"),
    (r"alt\s*\(sgpt\)|sgpt|alt", "Liver panel", "ALT"),
)
VALUE = re.compile(
    r"^\s*(?P<value>[<>≤≥]?\s*\d+(?:[.,]\d+)?|negative|positive|negatif|positif)"
    r"\s*(?P<flag>high|low|tinggi|rendah|[HL](?![a-z]))?",
    re.I,
)
UNIT = re.compile(r"mg/dL|g/dL|mmol/L|IU/L|U/L|%|[x×]10[Ee^]?\d+/[uµ]L", re.I)
RANGE = re.compile(
    r"^\s*(\d+(?:[.,]\d+)?\s*[-–]\s*\d+(?:[.,]\d+)?"
    r"|(?:[<>]\s*OR\s*=|[<>]=?|[≤≥])\s*\d+(?:[.,]\d+)?)", re.I,
)


def parse_line(line: str, page: int):
    for pattern, group, label in TESTS:
        name = re.match(rf"^({pattern})(?=\s|:|$)", line, re.I)
        if not name:
            continue
        tail = line[name.end():].lstrip(" :")
        match = VALUE.match(tail)
        if not match:
            return None
        fields = {key: (value or "").strip() for key, value in match.groupdict().items()}
        remainder = tail[match.end():].strip()
        unit = UNIT.match(remainder)
        limits = RANGE.match(remainder[unit.end():] if unit else remainder)
        if not unit and limits:
            unit = UNIT.match(remainder[limits.end():].lstrip())
        fields["unit"] = unit.group() if unit else ""
        fields["range"] = limits.group(1) if limits else ""
        return {"group": group, "label": label, "source_label": name.group(), "page": page,
                "source": line, **fields}
    return None


def lines_from_boxes(boxes, tolerance):
    """Group neighboring words by baseline, preserving horizontal cell order."""
    rows = []
    for y, x, text in sorted(boxes):
        if not rows or y - rows[-1][0] > tolerance:
            rows.append((y, []))
        rows[-1][1].append((x, text))
    return [" ".join(text for _, text in sorted(row)) for _, row in rows]


@lru_cache(maxsize=1)
def ocr_engine():
    from rapidocr_onnxruntime import RapidOCR
    return RapidOCR(intra_op_num_threads=2, inter_op_num_threads=2)


def ocr_lines(png):
    from io import BytesIO
    from PIL import Image

    boxes = []
    with Image.open(BytesIO(png)) as image:
        sections = 3 if image.height >= 1500 else 1
        for index in range(sections):
            start = index * image.height // sections
            end = (index + 1) * image.height // sections
            top = max(0, start - 45)
            tile = image.crop((0, top, image.width, min(image.height, end + 45)))
            buffer = BytesIO()
            tile.save(buffer, format="PNG")
            result, _ = ocr_engine()(buffer.getvalue(), max_side_len=2400)
            for box, text, confidence in result or []:
                y = top + sum(point[1] for point in box) / 4
                if start <= y < end and confidence >= .55:
                    boxes.append((y, min(point[0] for point in box), text))
    return lines_from_boxes(boxes, 10)


def extract(data):
    import fitz
    from PIL import Image
    from io import BytesIO

    methods, results, dates = set(), [], []
    if data.startswith(b"%PDF-"):
        with fitz.open(stream=data, filetype="pdf") as pdf:
            if pdf.needs_pass or not 1 <= len(pdf) <= 20:
                raise ValueError("Use an unlocked PDF with 1–20 pages.")
            pages = []
            for page in pdf:
                words = page.get_text("words")
                if len(words) >= 15:
                    methods.add("PDF text")
                    pages.append(lines_from_boxes([(w[1], w[0], w[4]) for w in words], 2.5))
                else:
                    methods.add("Image OCR")
                    scale = min(2, 2400 / max(page.rect.width, page.rect.height))
                    pages.append(ocr_lines(page.get_pixmap(matrix=fitz.Matrix(scale, scale)).tobytes("png")))
    else:
        with Image.open(BytesIO(data)) as image:
            if image.format not in {"JPEG", "PNG"} or image.width * image.height > 20_000_000:
                raise ValueError("Use a JPEG or PNG image under 20 megapixels.")
            image.thumbnail((2400, 2400))
            buffer = BytesIO()
            image.convert("RGB").save(buffer, format="PNG")
            pages = [ocr_lines(buffer.getvalue())]
            methods.add("Image OCR")
    for number, lines in enumerate(pages, 1):
        for line in lines:
            row = parse_line(line, number)
            if row:
                results.append(row)
            if re.search(r"date issued|date collected|tanggal pengambilan|tanggal pemeriksaan|tanggal terbit", line, re.I):
                dates.append({"page": number, "source": line})
    return {"rows": results, "date_evidence": dates, "methods": sorted(methods)}


@router.post("/api/mcu/extract")
async def extract_mcu(request: Request):
    from starlette.concurrency import run_in_threadpool

    if os.getenv("JAGSI_LOCAL_MCU") != "1" or not request.client or request.client.host not in {"127.0.0.1", "::1"}:
        raise HTTPException(404)
    if request.headers.get("origin") not in {"http://127.0.0.1:3095", "http://localhost:3095", "http://127.0.0.1:3096"}:
        raise HTTPException(403)
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > LIMIT:
            raise HTTPException(413, "The upload limit is 15 MB.")
        data.extend(chunk)
    if not data.startswith((b"%PDF-", b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n")):
        raise HTTPException(422, "Upload a PDF, JPEG, or PNG.")
    try:
        return await run_in_threadpool(extract, bytes(data))
    except ImportError as exc:
        raise HTTPException(503, "Local OCR dependencies are unavailable.") from exc
    except Exception as exc:
        raise HTTPException(422, "Could not read this report. Try a clear photo or enter results manually.") from exc
