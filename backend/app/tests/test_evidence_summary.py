"""Check combined summaries over all supported evidence-state combinations."""
from itertools import product

import unittest

from app.evidence_summary import summarize


CASES = list(product(
    ("absent", "high", "low", "unmarked"), (False, True), (False, True),
    (False, True), (False, True)))
def check_case(lab, watch, sim, late, alert):
    rows = [] if lab == "absent" else [
        {"label": "LDL cholesterol", "value": "<82.5", "unit": "mg/dL", "flag": lab}]
    text = summarize(lab_date="2026-05-02", reviewed_rows=rows, watch_time="09.42 WIB",
                     readings=[("SpO2", "97.1", "%")] if watch else [],
                     simulated=sim, stale=late, active_alert=alert)
    assert ("LDL cholesterol <82.5 mg/dL" in text) == bool(rows)
    assert ("2026-05-02" in text) == bool(rows)
    assert ("SpO2 97.1 %" in text and "09.42 WIB" in text) == watch
    assert ("Simulasi jam" in text) == (sim and watch)
    assert ("tinggi" in text) == (lab == "high")
    assert ("rendah" in text) == (lab == "low")
    assert ("tertunda" in text) == late
    assert text.startswith("Ada peringatan aktif") == alert
    assert ("Belum ada hasil MCU" in text) == (not rows)


class EvidenceSummaryTest(unittest.TestCase):
    def test_combinations(self):
        for case in CASES:
            with self.subTest(case=case):
                check_case(*case)

    def test_daily_recommendations(self):
        from app.evidence_summary import daily_brief
        row = {"label": "LDL cholesterol", "value": "142", "unit": "mg/dL", "flag": "H"}
        brief = daily_brief(wearer="Bu Sari", structured=True, reviewed_rows=[row], simulated=True)
        self.assertIn("pepes ikan", brief["Pilihan makan"])
        self.assertIn("Bu Sari", brief["Kebiasaan hari ini"])
        row["flag"] = ""
        self.assertIn("pantangan khusus", daily_brief(wearer="Bu Sari", structured=True, reviewed_rows=[row])["Pilihan makan"])
        self.assertNotIn("Pilihan makan", daily_brief(wearer="Bu Sari", structured=True, active_alert=True))

    def test_default_bullets(self):
        from app.evidence_summary import daily_brief
        for alert, count in [(False, 3), (True, 2)]:
            lines = daily_brief(wearer="Bu Sari", active_alert=alert).splitlines()
            self.assertEqual(len(lines), count)
            self.assertTrue(all(line.startswith("- **") for line in lines))
