import os
import sys
import unittest
from pathlib import Path


root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)


class TestWorkspaceDefaultWidgetsRegression(unittest.TestCase):
    def test_restore_falls_back_to_defaults_when_saved_items_are_invalid(self):
        widgets_js = Path(root_dir, "static/js/widgets.js").read_text(encoding="utf-8")

        self.assertIn("restoreDefaultWidgets()", widgets_js)
        self.assertIn("this.addWidget('channel-analytics', {}, { skipSave: true })", widgets_js)
        self.assertIn("this.addWidget('minified-stats', {}, { skipSave: true })", widgets_js)
        self.assertIn("const validItems = saved", widgets_js)
        self.assertIn("if (validItems.length)", widgets_js)
        self.assertIn("} else {\n                this.restoreDefaultWidgets();\n            }", widgets_js)

    def test_local_widget_state_must_be_array(self):
        widgets_js = Path(root_dir, "static/js/widgets.js").read_text(encoding="utf-8")

        self.assertIn("return Array.isArray(parsed) ? parsed : []", widgets_js)

    def test_widgets_module_has_no_escaped_template_ticks(self):
        widgets_js = Path(root_dir, "static/js/widgets.js").read_text(encoding="utf-8")

        self.assertNotIn("\\`", widgets_js)

    def test_widget_mount_failure_is_contained(self):
        widgets_js = Path(root_dir, "static/js/widgets.js").read_text(encoding="utf-8")

        self.assertIn("try {\n            widget.mount(this.root);\n        } catch (error) {", widgets_js)
        self.assertIn('console.error(`Failed to mount dashboard widget "${type}":`, error);', widgets_js)
        self.assertIn("this.widgets.delete(widget.id);", widgets_js)
        self.assertIn("return null;", widgets_js)

    def test_restore_falls_back_if_all_valid_items_fail_to_mount(self):
        widgets_js = Path(root_dir, "static/js/widgets.js").read_text(encoding="utf-8")

        self.assertIn("const mountedWidgets = validItems", widgets_js)
        self.assertIn(".map(item => this.addWidget(item.type, item, { skipSave: true }))", widgets_js)
        self.assertIn(".filter(Boolean);", widgets_js)
        self.assertIn("if (!mountedWidgets.length) {\n                    this.restoreDefaultWidgets();\n                }", widgets_js)

    def test_youtube_metrics_uses_stable_widget_api(self):
        widgets_js = Path(root_dir, "static/js/widgets.js").read_text(encoding="utf-8")
        youtube_section = widgets_js.split("class YouTubeMetricsWidget", 1)[1].split("class ChannelAnalyticsWidget", 1)[0]

        self.assertNotIn("super.renderShell();", youtube_section)
        self.assertNotIn("this.getWidgetDateHTML()", youtube_section)
        self.assertNotIn("this.bindDateSync()", youtube_section)
        self.assertNotIn("window.state?.channels", youtube_section)
        self.assertNotIn("window.initChartUI", youtube_section)
        self.assertNotIn("window.renderActiveChart", youtube_section)
        self.assertNotIn("this.workspace.saveLayout()", youtube_section)
        self.assertIn("leftHeader.insertBefore(this.renderDateSyncMenu(), limitControl);", youtube_section)
        self.assertIn("return state.allChannels.map(channel => channel.channel_id).filter(Boolean);", youtube_section)


if __name__ == "__main__":
    unittest.main()
