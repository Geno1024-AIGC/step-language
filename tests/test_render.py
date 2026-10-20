from __future__ import annotations

import gzip
import json
import re
import unittest
from pathlib import Path

from steplang import parse, parse_file, render

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "repair-computer.step"


class RenderExampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.doc = parse_file(EXAMPLE)
        cls.html = render(cls.doc)

    def test_self_contained(self) -> None:
        self.assertNotIn('<link rel="stylesheet"', self.html)
        self.assertNotIn("<script src=", self.html)
        self.assertNotIn('src="http', self.html)
        self.assertNotIn('href="http', self.html)
        self.assertIn('name="viewport" content="width=device-width', self.html)
        self.assertIn("@media (max-width: 900px)", self.html)

    def test_document_shell(self) -> None:
        self.assertIn('<html lang="zh-CN"', self.html)
        self.assertIn('class="no-js"', self.html)
        self.assertIn("<title>电脑无法开机排查</title>", self.html)
        self.assertIn("--accent:#2563eb", self.html)
        self.assertIn("8 个步骤", re.search(r"<footer.*?</footer>", self.html, re.S).group(0))

    def test_embedded_data(self) -> None:
        match = re.search(
            r'<script type="application/json" id="step-data">(.*?)</script>',
            self.html,
            re.S,
        )
        self.assertIsNotNone(match)
        data = json.loads(match.group(1))
        self.assertEqual(data["id"], "repair-computer")
        self.assertEqual(data["start"], "safety")
        self.assertEqual(len(data["steps"]), 8)
        self.assertEqual(data["steps"][0]["id"], "safety")
        self.assertEqual(data["steps"][-1]["next"], "done")

    def test_gzip_is_small(self) -> None:
        compressed = gzip.compress(self.html.encode("utf-8"), 9)
        self.assertLess(len(compressed), 40 * 1024)
        self.assertLess(len(self.html.encode("utf-8")), 120 * 1024)


class RenderSafetyTests(unittest.TestCase):
    def test_script_breakout_is_escaped(self) -> None:
        doc = parse(
            "@title T\n== a | </script><img src=x onerror=alert(1)>\n"
            "body </script><script>alert(2)</script>\n"
        )
        html = render(doc)
        self.assertNotIn("</script><img", html)
        self.assertNotIn("<script>alert(2)</script>", html)
        self.assertIn("\\u003c/script\\u003e", html)
        match = re.search(
            r'<script type="application/json" id="step-data">(.*?)</script>',
            html,
            re.S,
        )
        data = json.loads(match.group(1))
        self.assertEqual(data["steps"][0]["title"], "</script><img src=x onerror=alert(1)>")

    def test_bad_accent_falls_back(self) -> None:
        doc = parse("@title T\n@accent #abc\n== a | A\n")
        html = render(doc)
        self.assertIn("--accent:#abc", html)

    def test_english_ui(self) -> None:
        doc = parse("@title T\n@lang en\n== a | A\n? Go?\n* Yes -> done\n")
        html = render(doc)
        self.assertIn('<html lang="en"', html)
        self.assertIn("Skip to content", html)
        self.assertIn("Steps", html)
        self.assertIn('aria-label="Progress"', html)
        self.assertIn('"Finish"', html)


if __name__ == "__main__":
    unittest.main()
