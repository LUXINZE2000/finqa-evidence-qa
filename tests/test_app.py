import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest


class AppTests(unittest.TestCase):
    def test_keyword_flow_without_api_key(self):
        at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run(timeout=30)
        self.assertFalse(at.exception)
        at.radio[0].set_value("Keyword evidence only").run()
        at.button[0].click().run(timeout=30)
        self.assertFalse(at.exception)
        self.assertFalse(at.error)
        self.assertEqual(len(at.expander), 3)


if __name__ == "__main__":
    unittest.main()
