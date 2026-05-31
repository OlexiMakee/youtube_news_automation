import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from scripts import compact_memory


class TestCompactMemory(unittest.TestCase):
    def test_redacts_secret_like_values(self):
        text = "OPENAI_API_KEY=sk-testsecretvalue123456789"
        self.assertNotIn("sk-testsecret", compact_memory.redact(text))
        self.assertIn("[REDACTED]", compact_memory.redact(text))

    def test_python_pointer_uses_structure_not_raw_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.py"
            path.write_text("import sqlite3\n\ndef update_views(video_id):\n    return video_id\n", encoding="utf-8")
            pointer = compact_memory.build_pointer(path, path.read_text(encoding="utf-8"), 120)
        self.assertEqual(pointer["meta"]["layer"], "domain-layer")
        self.assertIn("update_views:3", pointer["meta"]["functions"])
        self.assertIn("sqlite3", pointer["meta"]["dependencies"])

    def test_jsonl_summary_counts_statuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "admin_proposals.jsonl"
            path.write_text(
                json.dumps({"id": 1, "type": "bug", "status": "done", "desc": "x"}) + "\n"
                + json.dumps({"id": 2, "type": "feature", "desc": "y"}) + "\n",
                encoding="utf-8",
            )
            summary = compact_memory.jsonl_summary(path, 80)
        self.assertEqual(summary["row_count"], 2)
        self.assertEqual(summary["status_counts"]["done"], 1)
        self.assertEqual(summary["status_counts"]["active"], 1)


if __name__ == "__main__":
    unittest.main()
