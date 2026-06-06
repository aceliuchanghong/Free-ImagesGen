from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from free_imagegen.cli import main  # noqa: E402


class CliTests(unittest.TestCase):
    def test_generate_svg_without_external_renderer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "cover.svg"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main(
                    [
                        "generate",
                        "--prompt",
                        "text cover, title Local First",
                        "--format",
                        "svg",
                        "--output",
                        str(output),
                    ]
                )
            self.assertEqual(code, 0)
            self.assertTrue(output.exists())
            self.assertEqual(json.loads(stdout.getvalue())["svg"], str(output.resolve()))

    def test_validate_plan_command(self) -> None:
        template = ROOT / "src" / "free_imagegen" / "resources" / "story-plan.template.json"
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main(["validate-plan", str(template)])
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(stdout.getvalue())["valid"])


if __name__ == "__main__":
    unittest.main()
