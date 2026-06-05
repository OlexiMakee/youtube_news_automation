import os
import sys
import unittest
from pathlib import Path


root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)


class TestOperatorIngestUIContract(unittest.TestCase):
    def test_template_exposes_preview_first_ingestion_console(self):
        html = Path(root_dir, "templates/index.html").read_text(encoding="utf-8")

        self.assertIn('id="operator-ingest-console"', html)
        self.assertIn('id="operator-ingest-source"', html)
        self.assertIn('id="operator-ingest-input"', html)
        self.assertIn("runIngestionPreview()", html)
        self.assertIn("runIngestionPersist()", html)

    def test_ui_loads_connector_metadata_and_avoids_row_persist(self):
        ui_js = Path(root_dir, "static/js/ui.js").read_text(encoding="utf-8")

        self.assertIn('adminFetch("/api/source-connectors")', ui_js)
        self.assertIn("_renderIngestionConsole(sources, connectors)", ui_js)
        self.assertIn('onclick="prepareIngestSource(${source.id})"', ui_js)
        self.assertNotIn('onclick="runIngest(${source.id})"', ui_js)
        self.assertIn("export async function runIngestionPreview()", ui_js)
        self.assertIn("export async function runIngestionPersist()", ui_js)
        self.assertIn("persist: Boolean(persist)", ui_js)
        self.assertIn("payload.allow_tier_e = true", ui_js)

    def test_app_exports_ingestion_console_handlers(self):
        app_js = Path(root_dir, "static/js/app.js").read_text(encoding="utf-8")

        self.assertIn("prepareIngestSource,", app_js)
        self.assertIn("runIngestionPreview,", app_js)
        self.assertIn("runIngestionPersist,", app_js)
        self.assertIn("window.prepareIngestSource = prepareIngestSource", app_js)
        self.assertIn("window.runIngestionPreview = runIngestionPreview", app_js)
        self.assertIn("window.runIngestionPersist = runIngestionPersist", app_js)

    def test_css_bounds_ingestion_console_surfaces(self):
        css = Path(root_dir, "static/css/style.css").read_text(encoding="utf-8")

        self.assertIn(".operator-runtime-section-wide", css)
        self.assertIn("max-height: 340px", css)
        self.assertIn("max-height: 360px", css)
        self.assertIn(".operator-ingest-record", css)


if __name__ == "__main__":
    unittest.main()
