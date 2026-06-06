from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from . import _engine

_ENGINE_LOCK = threading.RLock()


@dataclass(frozen=True, slots=True)
class RenderOptions:
    theme: str = "auto"
    density: str = "auto"
    series_style: str = "auto"
    section_role: str = "auto"
    surface_style: str = "auto"
    accent: str = "auto"
    tone: str = "auto"
    decor_level: str = "auto"
    emoji_policy: str = "auto"
    emoji_render_mode: str = "auto"
    cover_layout: str = "auto"
    hero_emoji: str = ""


def _validate_dimensions(width: int, height: int) -> None:
    if not 1 <= width <= 8192 or not 1 <= height <= 8192:
        raise ValueError("width and height must be between 1 and 8192")


def _apply_options(prompt: str, options: RenderOptions | None) -> str:
    if options is None:
        return prompt
    return _engine._append_render_controls(
        prompt,
        options.theme,
        options.density,
        options.surface_style,
        options.accent,
        options.series_style,
        options.section_role,
        options.tone,
        options.decor_level,
        options.emoji_policy,
        options.emoji_render_mode,
        options.cover_layout,
        options.hero_emoji,
    )


def compose_svg(
    prompt: str,
    width: int = 1024,
    height: int = 1024,
    *,
    options: RenderOptions | None = None,
) -> str:
    if not prompt.strip():
        raise ValueError("prompt cannot be empty")
    _validate_dimensions(width, height)
    with _ENGINE_LOCK:
        return _engine._compose_svg(_apply_options(prompt, options), width, height)


def write_svg(
    prompt: str,
    output: str | Path,
    width: int = 1024,
    height: int = 1024,
    *,
    options: RenderOptions | None = None,
) -> dict[str, Any]:
    output_path = Path(output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        compose_svg(prompt, width, height, options=options), encoding="utf-8"
    )
    return {
        "mode": "local-prompt-to-svg",
        "prompt": prompt,
        "svg": str(output_path),
        "width": width,
        "height": height,
    }


def generate_image(
    prompt: str,
    output: str | Path,
    width: int = 1024,
    height: int = 1024,
    *,
    svg_output: str | Path | None = None,
    keep_svg: bool = False,
    options: RenderOptions | None = None,
) -> dict[str, Any]:
    if not prompt.strip():
        raise ValueError("prompt cannot be empty")
    _validate_dimensions(width, height)
    with _ENGINE_LOCK:
        return _engine.generate_image(
            _apply_options(prompt, options),
            output,
            width,
            height,
            svg_output=svg_output,
            keep_svg=keep_svg,
        )


def generate_image_from_svg(
    svg_markup: str,
    output: str | Path,
    width: int = 1024,
    height: int = 1024,
    *,
    svg_output: str | Path | None = None,
    keep_svg: bool = False,
) -> dict[str, Any]:
    _validate_dimensions(width, height)
    with _ENGINE_LOCK:
        return _engine.generate_image_from_svg_markup(
            svg_markup,
            output,
            width,
            height,
            svg_output=svg_output,
            keep_svg=keep_svg,
        )


def load_story_plan(path: str | Path) -> dict[str, Any]:
    plan_path = Path(path).expanduser().resolve()
    try:
        data = json.loads(plan_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"invalid story plan JSON at line {exc.lineno}: {exc.msg}"
        ) from exc
    return validate_story_plan(data)


def validate_story_plan(plan: Any) -> dict[str, Any]:
    return _engine._validate_story_plan(plan)


def lint_story_plan(plan: dict[str, Any]) -> list[dict[str, str]]:
    return _engine._story_plan_lints(plan)


def generate_story(
    prompt: str,
    output_dir: str | Path,
    width: int = 1080,
    height: int = 1440,
    *,
    strategy: str = "auto",
    mode: str = "all",
    story_images: list[str] | None = None,
    story_plan: dict[str, Any] | None = None,
    keep_svg: bool = False,
    options: RenderOptions | None = None,
) -> dict[str, Any]:
    if not prompt.strip():
        raise ValueError("prompt cannot be empty")
    _validate_dimensions(width, height)
    normalized_plan = (
        validate_story_plan(story_plan) if story_plan is not None else None
    )
    if strategy not in {"auto", "story", "dense", "visual"}:
        raise ValueError(f"unsupported story strategy: {strategy}")
    if mode not in {"all", "outline-only", "prompts-only", "images-only"}:
        raise ValueError(f"unsupported story mode: {mode}")
    with _ENGINE_LOCK:
        return _engine.generate_article_story(
            _apply_options(prompt, options),
            output_dir,
            width,
            height,
            strategy=strategy,
            mode=mode,
            story_images=story_images or [],
            story_plan=normalized_plan,
            keep_svg=keep_svg,
        )


def generate_openclaw_assets(
    project_dir: str | Path,
    prompt: str,
    *,
    keep_svg: bool = False,
) -> dict[str, Any]:
    if not prompt.strip():
        raise ValueError("prompt cannot be empty")
    with _ENGINE_LOCK:
        return _engine.generate_openclaw_assets(project_dir, prompt, keep_svg=keep_svg)


def default_output_path(
    prompt: str, suffix: str = ".png", *, prefix: str = "image"
) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = _engine._slugify(prompt)[:36] or prefix
    return Path.cwd() / "output" / f"{stamp}-{prefix}-{slug}{suffix}"


def default_story_dir(title: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = _engine._slugify(title)[:36] or "story"
    return Path.cwd() / "output" / f"{stamp}-story-{slug}"


def generate_image_from_idea(
    idea: str,
    output: str | Path,
    width: int = 1024,
    height: int = 1024,
    *,
    keep_svg: bool = False,
    options: RenderOptions | None = None,
) -> dict[str, Any]:
    """End-to-end: simple idea → LLM → structured prompt → render single image."""
    from .llm import generate_structured_prompt

    if not idea.strip():
        raise ValueError("idea cannot be empty")
    prompt = generate_structured_prompt(idea)
    return generate_image(
        prompt,
        output,
        width,
        height,
        keep_svg=keep_svg,
        options=options,
    )


def generate_story_from_idea(
    idea: str,
    output_dir: str | Path,
    width: int = 1080,
    height: int = 1440,
    *,
    num_cards: int | None = None,
    strategy: str = "auto",
    keep_svg: bool = False,
    options: RenderOptions | None = None,
) -> dict[str, Any]:
    """End-to-end: simple idea → LLM → story-plan JSON → render card set."""
    from .llm import generate_story_plan

    if not idea.strip():
        raise ValueError("idea cannot be empty")
    plan = generate_story_plan(idea, num_cards=num_cards)
    title = plan.get("title", idea)
    return generate_story(
        title,
        output_dir,
        width,
        height,
        strategy=strategy,
        story_plan=plan,
        keep_svg=keep_svg,
        options=options,
    )
