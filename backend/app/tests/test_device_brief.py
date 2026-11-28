"""Regression checks for the offline daily brief path."""
from unittest import TestCase
from unittest.mock import Mock, patch
import json

from app.brief_worker import infer_pattern
from app.device_brief import device_brief
from app.local_brief import MODEL_ID, plans


class DeviceBriefTest(TestCase):
    def setUp(self):
        self.ctx = dict(latest=None, alerts_24h=[])
        self.row = dict(label="LDL cholesterol", value="<142", unit="mg/dL", flag="H")
        infer_pattern.cache_clear()
        self.addCleanup(infer_pattern.cache_clear)

    @patch("app.brief_worker.subprocess.run")
    @patch("app.device_brief.build_context")
    def test_served_pattern_preserves_evidence(self, context, run):
        context.return_value = self.ctx
        state = dict(watch="kosong", alert=False, ldl_high=True)
        run.return_value = Mock(stdout=json.dumps({"model": MODEL_ID, "pattern": plans(state)[0]}))
        result = device_brief(None, "test-watch", "Bu Sari", [self.row], "2026-05-02")
        self.assertEqual(result["source"], "local_llm")
        self.assertIn("LDL cholesterol <142 mg/dL", result["text"])
        self.assertIn("2026-05-02", result["text"])
        self.assertEqual(json.loads(run.call_args.kwargs["input"]), state)
        device_brief(None, "another-watch", "Another wearer", [self.row], None)
        run.assert_called_once()

    @patch("app.brief_worker.subprocess.run")
    @patch("app.device_brief.build_context")
    def test_unavailable_or_invalid_model_stays_local(self, context, run):
        context.return_value = {**self.ctx, "alerts_24h": [{"status": "open"}]}
        for response in (OSError(), Mock(stdout='{"pattern":"unverified"}')):
            run.side_effect = [response]
            result = device_brief(None, "test", "Bu Sari", [], None)
            self.assertEqual(result["source"], "rules")
            self.assertIn("Langkah sekarang", result["text"])
            self.assertNotIn("Pilihan makan", result["text"])
