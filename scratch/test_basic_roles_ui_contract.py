import os
import sys
import unittest
from pathlib import Path


root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)


class TestBasicRolesUIContract(unittest.TestCase):
    def test_state_and_auth_map_backend_roles_to_ui_roles(self):
        state_js = Path(root_dir, "static/js/state.js").read_text(encoding="utf-8")
        auth_js = Path(root_dir, "static/js/auth.js").read_text(encoding="utf-8")

        self.assertIn('userRole: "reader"', state_js)
        self.assertIn("authStatus: null", state_js)
        self.assertIn("function normalizeUiRole(status)", auth_js)
        self.assertIn('role === "analyst"', auth_js)
        self.assertIn('return "reader"', auth_js)
        self.assertIn("state.userRole = normalizeUiRole(data)", auth_js)

    def test_ui_has_declarative_role_visibility_policy(self):
        ui_js = Path(root_dir, "static/js/ui.js").read_text(encoding="utf-8")

        self.assertIn("const ROLE_LEVELS", ui_js)
        self.assertIn("reader: 1", ui_js)
        self.assertIn("analyst: 2", ui_js)
        self.assertIn("admin: 3", ui_js)
        self.assertIn("export function applyRoleVisibility()", ui_js)
        self.assertIn('document.querySelectorAll("[data-role-min]")', ui_js)
        self.assertIn("element.hidden = currentLevel < requiredLevel", ui_js)
        self.assertIn('switchSection("analytics-tab"', ui_js)
        self.assertIn('switchAgentRole("user")', ui_js)
        self.assertIn("applyRoleVisibility()", ui_js)

    def test_template_marks_role_gated_controls(self):
        html = Path(root_dir, "templates/index.html").read_text(encoding="utf-8")

        self.assertIn('id="menu-item-terminal" data-tab="terminal-tab" data-role-min="admin"', html)
        self.assertIn('class="sidebar-widget-library" data-role-min="analyst"', html)
        self.assertIn('class="sidebar-proposals" data-role-min="admin"', html)
        self.assertIn('id="btn-generate-brief" data-role-min="analyst"', html)
        self.assertIn('id="chat-tab-admin" style=', html)
        self.assertIn('data-role-min="admin" onclick="downloadVideoFromModal()"', html)
        self.assertIn('data-role-min="admin" onclick="scrapeDetailsFromModal()"', html)
        self.assertIn('data-role-min="admin" onclick="getTranscriptFromModal()"', html)

    def test_startup_exports_and_applies_role_visibility(self):
        app_js = Path(root_dir, "static/js/app.js").read_text(encoding="utf-8")
        api_js = Path(root_dir, "static/js/api.js").read_text(encoding="utf-8")

        self.assertIn("applyRoleVisibility", app_js)
        self.assertIn("window.applyRoleVisibility = applyRoleVisibility", app_js)
        self.assertIn("await loadEntitlements();", app_js)
        self.assertIn("applyRoleVisibility();", app_js)
        self.assertIn("await loadAuthStatus(true)", api_js)


if __name__ == "__main__":
    unittest.main()
