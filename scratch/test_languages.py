import os
import sys
import unittest
from pathlib import Path

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)


class TestLanguagesUIContract(unittest.TestCase):
    def test_language_options_in_html(self):
        html_path = Path(root_dir, "templates/index.html")
        self.assertTrue(html_path.exists())
        html = html_path.read_text(encoding="utf-8")

        # Verify language selector dropdown options for Spanish (es), Portuguese (pt), Turkish (tr)
        self.assertIn('value="ua"', html)
        self.assertIn('value="en"', html)
        self.assertIn('value="es"', html)
        self.assertIn('value="pt"', html)
        self.assertIn('value="tr"', html)

    def test_translations_dictionary_has_languages(self):
        translations_path = Path(root_dir, "static/js/translations.js")
        self.assertTrue(translations_path.exists())
        trans = translations_path.read_text(encoding="utf-8")

        # Verify translations have maps for all required languages
        self.assertIn("ua: {", trans)
        self.assertIn("en: {", trans)
        self.assertIn("es: {", trans)
        self.assertIn("pt: {", trans)
        self.assertIn("tr: {", trans)


if __name__ == "__main__":
    unittest.main()
