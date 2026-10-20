from __future__ import annotations

import unittest
from pathlib import Path

from steplang import parse_file

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


class ExampleTests(unittest.TestCase):
    def test_examples_parse_without_warnings(self) -> None:
        paths = sorted(EXAMPLES.glob("*.step"))
        self.assertGreaterEqual(len(paths), 2)

        for path in paths:
            with self.subTest(example=path.name):
                doc = parse_file(path)
                self.assertEqual([], doc.warnings)
                self.assertGreater(len(doc.steps), 0)
