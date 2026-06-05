import os
import sys
import unittest
from pathlib import Path


root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)


class TestCompactGridRegression(unittest.TestCase):
    def test_widget_resize_is_bounded_and_restore_does_not_save_loop(self):
        widgets_js = Path(root_dir, "static/js/widgets.js").read_text(encoding="utf-8")

        self.assertIn("const MIN_WIDGET_WIDTH = 320", widgets_js)
        self.assertIn("dimensionLimits()", widgets_js)
        self.assertIn("Math.min(maxWidth, Math.max(MIN_WIDGET_WIDTH", widgets_js)
        self.assertIn("Math.min(maxHeight, Math.max(MIN_WIDGET_HEIGHT", widgets_js)
        self.assertIn("touch-action: none", Path(root_dir, "static/css/style.css").read_text(encoding="utf-8"))
        self.assertIn("skipSave", widgets_js)
        self.assertIn("this.isRestoring = true", widgets_js)
        self.assertIn("this.addWidget(item.type, item, { skipSave: true })", widgets_js)

    def test_local_admin_keeps_operator_runtime_visible(self):
        api_js = Path(root_dir, "static/js/api.js").read_text(encoding="utf-8")

        self.assertIn("loadAuthStatus", api_js)
        self.assertIn("authStatus?.admin", api_js)
        self.assertIn("state.entitlements.operator_runtime = true", api_js)


if __name__ == "__main__":
    unittest.main()
