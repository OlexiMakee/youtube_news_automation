import os
import sys
import unittest
from pathlib import Path


root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)


class TestBriefCopyUIContract(unittest.TestCase):
    def test_modal_contains_copy_brief_action_and_status(self):
        html = Path(root_dir, "templates/index.html").read_text(encoding="utf-8")

        self.assertIn("copyBriefMarkdownFromModal()", html)
        self.assertIn('data-i18n="btn_copy_brief"', html)
        self.assertIn('id="brief-copy-status"', html)

    def test_briefs_js_exposes_copy_handlers_and_clipboard_fallback(self):
        briefs_js = Path(root_dir, "static/js/briefs.js").read_text(encoding="utf-8")

        self.assertIn("export async function copyBriefMarkdown(briefId)", briefs_js)
        self.assertIn("export async function copyBriefMarkdownFromModal()", briefs_js)
        self.assertIn("navigator.clipboard?.writeText", briefs_js)
        self.assertIn('document.execCommand("copy")', briefs_js)
        self.assertIn("window.copyBriefMarkdown = copyBriefMarkdown", briefs_js)
        self.assertIn("window.copyBriefMarkdownFromModal = copyBriefMarkdownFromModal", briefs_js)
        self.assertIn("event.stopPropagation(); copyBriefMarkdown(${b.id})", briefs_js)

    def test_translations_include_copy_brief_label(self):
        translations = Path(root_dir, "static/js/translations.js").read_text(encoding="utf-8")

        self.assertEqual(translations.count("btn_copy_brief:"), 5)

    def test_styles_bound_copy_controls(self):
        css = Path(root_dir, "static/css/style.css").read_text(encoding="utf-8")

        self.assertIn(".brief-modal-actions", css)
        self.assertIn(".brief-copy-status", css)
        self.assertIn(".brief-row-copy-btn", css)


if __name__ == "__main__":
    unittest.main()
