from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from steplang.cli import _index_page, main

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "repair-computer.step"


def run_cli(args: list[str]) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = main(args)
    return code, stdout.getvalue(), stderr.getvalue()


class CliTests(unittest.TestCase):
    def test_check_example(self) -> None:
        code, out, err = run_cli(["check", str(EXAMPLE), "--strict"])
        self.assertEqual(code, 0)
        self.assertIn("ok:", out)
        self.assertEqual(err, "")

    def test_build_to_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "guide.html"
            code, out, _ = run_cli(["build", str(EXAMPLE), "-o", str(output)])
            self.assertEqual(code, 0)
            self.assertTrue(output.is_file())
            self.assertIn("<!doctype html>", output.read_text(encoding="utf-8"))
            self.assertIn("wrote", out)

    def test_build_to_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            code, _, _ = run_cli(["build", str(EXAMPLE), "-o", str(output_dir)])
            self.assertEqual(code, 0)
            self.assertTrue((output_dir / "repair-computer.html").is_file())

    def test_build_refuses_to_overwrite_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "keep.step"
            source.write_text("@title T\n== a | A\n", encoding="utf-8")
            code, _, err = run_cli(["build", str(source), "-o", str(source)])
            self.assertEqual(code, 1)
            self.assertIn("refusing", err)
            self.assertEqual(source.read_text(encoding="utf-8"), "@title T\n== a | A\n")

    def test_build_syntax_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "bad.step"
            source.write_text("== a | A\n", encoding="utf-8")
            code, _, err = run_cli(["build", str(source)])
            self.assertEqual(code, 1)
            self.assertIn("@title", err)

    def test_check_strict_warns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "warn.step"
            source.write_text(
                "@title T\n== a | A\n-> done\n== b | B\n-> done\n",
                encoding="utf-8",
            )
            code, _, err = run_cli(["check", str(source), "--strict"])
            self.assertEqual(code, 1)
            self.assertIn("not reachable", err)

    def test_guide(self) -> None:
        code, out, _ = run_cli(["guide"])
        self.assertEqual(code, 0)
        self.assertIn("== step-id |", out)
        self.assertIn("python3 -m steplang build", out)

    def test_index_page(self) -> None:
        page = _index_page(EXAMPLE.parent)
        self.assertIn("电脑无法开机排查", page)
        self.assertIn("/repair-computer.step", page)


if __name__ == "__main__":
    unittest.main()
