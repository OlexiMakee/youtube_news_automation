import os
import sys
import unittest
from pathlib import Path


root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)


class TestSourceRecordsUIContract(unittest.TestCase):
    def test_operator_runtime_contains_source_records_panel(self):
        html = Path(root_dir, "templates/index.html").read_text(encoding="utf-8")

        self.assertIn("Source Records", html)
        self.assertIn('id="operator-source-records"', html)

    def test_ui_loads_and_renders_source_records(self):
        ui_js = Path(root_dir, "static/js/ui.js").read_text(encoding="utf-8")

        self.assertIn('adminFetch("/api/source-records?limit=8")', ui_js)
        self.assertIn("function _renderSourceRecords(data)", ui_js)
        self.assertIn("_renderSourceRecords(records)", ui_js)
        self.assertIn("Source records unavailable.", ui_js)
        self.assertIn("record.has_content_hash", ui_js)

    def test_governance_route_registered(self):
        route_py = Path(root_dir, "app/routes/governance.py").read_text(encoding="utf-8")

        self.assertIn('@governance_bp.route("/api/source-records", methods=["GET"])', route_py)
        self.assertIn("list_source_records", route_py)


if __name__ == "__main__":
    unittest.main()
