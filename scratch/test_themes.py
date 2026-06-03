import os
import sys
import unittest
from pathlib import Path

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)


class TestThemesUIContract(unittest.TestCase):
    def test_theme_options_in_html(self):
        html_path = Path(root_dir, "templates/index.html")
        self.assertTrue(html_path.exists())
        html = html_path.read_text(encoding="utf-8")

        # Verify correct order and presence of theme selectors:
        # Білий (light), білий сепія (sepia), відтінки сірого теплий (grey-warm),
        # відтінки сірого (grey), відтінки сірого холодний (grey-cold), темний синій (dark-blue), темний (dark-black)
        
        selectors = [
            'value="light"',
            'value="sepia"',
            'value="grey-warm"',
            'value="grey"',
            'value="grey-cold"',
            'value="dark-blue"',
            'value="dark-black"'
        ]
        
        last_index = -1
        for val in selectors:
            index = html.find(val)
            self.assertNotEqual(index, -1, f"Theme option {val} not found in index.html")
            self.assertGreater(index, last_index, f"Theme option {val} is not in the correct order")
            last_index = index

        # Verify custom inline style colors are applied on option tags for each style
        self.assertIn('value="light" style="background-color: #ffffff; color: #202124;"', html)
        self.assertIn('value="sepia" style="background-color: #fdf6e3; color: #433422;"', html)
        self.assertIn('value="grey-warm" style="background-color: #f5f5f0; color: #3e2723;"', html)
        self.assertIn('value="grey" style="background-color: #eeeeee; color: #212121;"', html)
        self.assertIn('value="grey-cold" style="background-color: #eceff1; color: #263238;"', html)
        self.assertIn('value="dark-blue" style="background-color: #1e293b; color: #f8fafc;"', html)
        self.assertIn('value="dark-black" style="background-color: #121216; color: #f1f3f4;"', html)

    def test_theme_styles_in_css(self):
        css_path = Path(root_dir, "static/css/style.css")
        self.assertTrue(css_path.exists())
        css = css_path.read_text(encoding="utf-8")

        # Verify theme rule blocks exist
        self.assertIn('[data-theme="grey-warm"]', css)
        self.assertIn('[data-theme="grey"]', css)
        self.assertIn('[data-theme="grey-cold"]', css)

    def test_theme_translations(self):
        translations_path = Path(root_dir, "static/js/translations.js")
        self.assertTrue(translations_path.exists())
        trans = translations_path.read_text(encoding="utf-8")

        # Verify translations exist for UA/EN
        self.assertIn("theme_grey_warm:", trans)
        self.assertIn("theme_grey:", trans)
        self.assertIn("theme_grey_cold:", trans)


if __name__ == "__main__":
    unittest.main()
