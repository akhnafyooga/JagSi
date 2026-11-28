"""Exercise JSON request rejection through the daily-brief ASGI route."""
import unittest
from unittest.mock import patch

import httpx
from app.main import app


class IntakeValidationTest(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_payloads_stop_before_inference(self):
        invalid = [
            {"reviewed_rows": [{"label": "  ", "value": "90"}]},
            {"reviewed_rows": [{"label": "Glucose", "value": "  "}]},
            {"reviewed_rows": [{"label": "LDL\nsecond line", "value": "110"}]},
            {"lab_date": "2026-02-30"},
            {"reviewed_rows": [{"label": "Glucose", "value": "90"}] * 101},
            {"reviewed_rows": [{"label": "Glucose", "value": "1" * 49}]},
        ]
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                     base_url="http://test") as client:
            with patch("app.main.device_brief") as infer:
                for payload in invalid:
                    with self.subTest(payload=str(payload)[:70]):
                        response = await client.post("/api/devices/test/daily-brief", json=payload)
                        self.assertEqual(response.status_code, 422)
                infer.assert_not_called()
