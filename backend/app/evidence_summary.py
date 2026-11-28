"""Offline JagSi evidence summary. Inputs belong to one verified device/person."""
import json
from pathlib import Path

MODEL = Path(__file__).with_name("summary_order.json")
KINDS = ("alert", "stale", "flagged", "watch", "lab", "simulated")


def summarize(*, lab_date=None, reviewed_rows=(), watch_time=None, readings=(),
              simulated=False, stale=False, active_alert=False):
    scores = json.loads(MODEL.read_text())["scores"]
    blocks = []
    if active_alert:
        blocks.append(("alert", "Ada peringatan aktif pada perangkat. Periksa rincian peringatan."))
    if stale:
        blocks.append(("stale", "Pembaruan jam tertunda. Angka terakhir belum menggambarkan kondisi saat ini."))
    if readings and watch_time:
        values = ", ".join(f"{label} {value} {unit}" for label, value, unit in readings)
        source = "Simulasi jam" if simulated else "Catatan jam"
        blocks.append(("simulated" if simulated else "watch", f"{source} pada {watch_time} mencatat {values}."))
    else:
        blocks.append(("watch", "Belum ada pembacaan jam dengan waktu yang terkonfirmasi."))
    labs = []
    flagged = False
    for row in reviewed_rows:
        if not row.get("label") or not row.get("value") or not row.get("unit"):
            raise ValueError("Each reviewed row requires label, value and unit.")
        flag = str(row.get("flag", "")).strip().lower()
        annotation = ""
        if flag in ("l", "low", "rendah", "h", "high", "tinggi"):
            flagged = True
            direction = "rendah" if flag in ("l", "low", "rendah") else "tinggi"
            annotation = f" (ditandai {direction} oleh lab)"
        labs.append(f"{row['label']} {row['value']} {row['unit']}{annotation}")
    if labs:
        when = f"tanggal {lab_date}" if lab_date else "dengan tanggal belum terkonfirmasi"
        blocks.append(("flagged" if flagged else "lab", f"Hasil MCU {when} mencatat " + ", ".join(labs) + "."))
    else:
        blocks.append(("lab", "Belum ada hasil MCU yang dikonfirmasi."))
    return " ".join(sentence for kind, sentence in sorted(blocks, key=lambda b: -scores[b[0]]))


def daily_brief(*, wearer, reviewed_rows=(), structured=False, **observations):
    """Render Markdown bullets, or return section fields for a structured client."""
    rows = list(reviewed_rows)
    overview = summarize(reviewed_rows=rows, **observations)
    sections = {f"Kabar {wearer} hari ini": overview}
    if observations.get("active_alert"):
        sections["Langkah sekarang"] = f"Segera cek keadaan {wearer} dan buka rincian peringatan."
        return sections if structured else _bullets(sections)
    if observations.get("simulated") or observations.get("stale") or not (
        observations.get("readings") and observations.get("watch_time")
    ):
        lifestyle = f"Tanyakan bagaimana perasaan {wearer} sebelum merencanakan aktivitas hari ini."
    else:
        lifestyle = (f"Ajak {wearer} mencatat kegiatan saat jam mengambil bacaan. "
                     "Catatan ini membantu keluarga membandingkan bacaan saat istirahat dan saat bergerak.")
    high_ldl = any(row["label"].strip().casefold() == "ldl cholesterol" and
                   str(row.get("flag", "")).strip().lower() in ("h", "high", "tinggi") for row in rows)
    if high_ldl:
        lifestyle += " Saat kontrol berikutnya, bawa hasil MCU untuk membahas kolesterol LDL."
        meals = (f"Jika sesuai dengan anjuran makan {wearer}, coba pepes ikan atau tahu kukus "
                 "sebagai pengganti lauk daging berlemak. Batasi makanan tinggi lemak jenuh, "
                 "misalnya daging berlemak dan masakan bersantan kental.")
    else:
        meals = (f"Ikuti pola makan yang biasa dianjurkan untuk {wearer}. "
                 "Data yang tersedia belum menjadi dasar untuk menyarankan pantangan khusus.")
    sections["Kebiasaan hari ini"] = lifestyle
    sections["Pilihan makan"] = meals
    return sections if structured else _bullets(sections)


def _bullets(sections):
    return "\n".join(f"- **{heading}.** {body}" for heading, body in sections.items())
