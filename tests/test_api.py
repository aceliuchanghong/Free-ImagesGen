from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from free_imagegen.api import (
    compose_svg,
    load_story_plan,
    validate_story_plan,
)


class ApiTests(unittest.TestCase):
    def test_compose_svg_uses_requested_dimensions(self) -> None:
        svg = compose_svg("文字封面，标题：本地图片生成", width=640, height=800)
        self.assertIn('width="640"', svg)
        self.assertIn('height="800"', svg)
        self.assertTrue(svg.startswith("<svg"))

    def test_load_bundled_story_plan_template(self) -> None:
        path = ROOT / "src" / "free_imagegen" / "resources" / "story-plan.template.json"
        plan = load_story_plan(path)
        self.assertGreaterEqual(len(plan["cards"]), 1)

    def test_invalid_story_plan_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_story_plan({"title": "missing cards"})

    def test_invalid_json_has_readable_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text("{", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "line 1"):
                load_story_plan(path)


if __name__ == "__main__":
    unittest.main()
