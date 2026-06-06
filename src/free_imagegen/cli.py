from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from . import __version__
from .api import (
    RenderOptions,
    default_output_path,
    default_story_dir,
    generate_image,
    generate_openclaw_assets,
    generate_story,
    lint_story_plan,
    load_story_plan,
    write_svg,
)


def _add_dimensions(parser: argparse.ArgumentParser, *, story: bool = False) -> None:
    parser.add_argument("--width", type=int, default=1080 if story else 1024)
    parser.add_argument("--height", type=int, default=1440 if story else 1024)


def _add_render_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--theme", choices=["auto", "light", "dark"], default="auto")
    parser.add_argument("--density", choices=["auto", "comfy", "compact"], default="auto")
    parser.add_argument("--series-style", choices=["auto", "loose", "unified"], default="auto")
    parser.add_argument("--section-role", choices=["auto", "cover", "chapter", "body", "summary"], default="auto")
    parser.add_argument("--surface-style", choices=["auto", "soft", "card", "minimal", "editorial"], default="auto")
    parser.add_argument("--accent", choices=["auto", "blue", "green", "warm", "rose"], default="auto")
    parser.add_argument("--tone", choices=["auto", "calm", "playful", "bold", "editorial"], default="auto")
    parser.add_argument("--decor-level", choices=["auto", "none", "low", "medium"], default="auto")
    parser.add_argument("--emoji-policy", choices=["auto", "none", "sparse", "expressive"], default="auto")
    parser.add_argument("--emoji-render-mode", choices=["auto", "font", "svg", "mono", "none"], default="auto")
    parser.add_argument("--cover-layout", choices=["auto", "title_first", "hero_emoji_top"], default="auto")
    parser.add_argument("--hero-emoji", default="")


def _render_options(args: argparse.Namespace) -> RenderOptions:
    return RenderOptions(
        theme=args.theme,
        density=args.density,
        series_style=args.series_style,
        section_role=args.section_role,
        surface_style=args.surface_style,
        accent=args.accent,
        tone=args.tone,
        decor_level=args.decor_level,
        emoji_policy=args.emoji_policy,
        emoji_render_mode=args.emoji_render_mode,
        cover_layout=args.cover_layout,
        hero_emoji=args.hero_emoji,
    )


def _read_prompt(args: argparse.Namespace) -> str:
    if getattr(args, "prompt_file", None):
        return Path(args.prompt_file).expanduser().read_text(encoding="utf-8")
    return args.prompt


def _run_create(args: argparse.Namespace) -> dict[str, Any]:
    """Handle the 'create' command: idea → LLM → render."""
    from .llm import generate_story_plan, generate_structured_prompt

    idea: str = args.idea
    mode: str = getattr(args, "mode", "image")
    options = _render_options(args)

    if mode == "story":
        # ── story mode: idea → LLM → story-plan JSON → render card set ──
        num_cards = getattr(args, "cards", None)
        plan = generate_story_plan(idea, num_cards=num_cards)
        title = plan.get("title", idea)
        output_dir = Path(args.output_dir).expanduser() if args.output_dir else default_story_dir(title)
        print(f'[create] LLM generated story plan: "{title}" ({len(plan.get("cards", []))} cards)', file=sys.stderr)
        return generate_story(
            title,
            output_dir,
            args.width,
            args.height,
            strategy="auto",
            story_plan=plan,
            keep_svg=args.keep_svg,
            options=options,
        )

    # ── image mode: idea → LLM → structured prompt → render single image ──
    prompt = generate_structured_prompt(idea)
    print(f'[create] LLM generated prompt: "{prompt}"', file=sys.stderr)
    suffix = ".svg" if args.format == "svg" else ".png"
    output = Path(args.output).expanduser() if args.output else default_output_path(prompt, suffix)

    if args.format == "svg":
        return write_svg(prompt, output, args.width, args.height, options=options)
    return generate_image(
        prompt,
        output,
        args.width,
        args.height,
        keep_svg=args.keep_svg,
        options=options,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="free-imagegen", description="LLM-powered prompt-to-image CLI renderer")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ── create: end-to-end LLM → image ──
    create_parser = subparsers.add_parser("create", help="Generate image(s) from a simple idea via LLM")
    create_parser.add_argument("idea", help="Your simple idea or topic")
    create_parser.add_argument("--mode", choices=["image", "story"], default="image",
                               help="image: single image; story: multi-page card set (default: image)")
    create_parser.add_argument("--cards", type=int, default=None,
                               help="Number of cards for story mode (optional)")
    create_parser.add_argument("-o", "--output", help="Output file path (image mode)")
    create_parser.add_argument("--output-dir", help="Output directory (story mode)")
    create_parser.add_argument("--format", choices=["png", "svg"], default="png")
    create_parser.add_argument("--keep-svg", action="store_true")
    _add_dimensions(create_parser)
    _add_render_options(create_parser)

    # ── generate: manual prompt ──
    generate_parser = subparsers.add_parser("generate", help="Generate one SVG or PNG image")
    prompt_group = generate_parser.add_mutually_exclusive_group(required=True)
    prompt_group.add_argument("--prompt")
    prompt_group.add_argument("--prompt-file")
    generate_parser.add_argument("-o", "--output")
    generate_parser.add_argument("--format", choices=["png", "svg"], default="png")
    generate_parser.add_argument("--svg-output")
    generate_parser.add_argument("--keep-svg", action="store_true")
    _add_dimensions(generate_parser)
    _add_render_options(generate_parser)

    story_parser = subparsers.add_parser("story", help="Generate an article card set")
    story_source = story_parser.add_mutually_exclusive_group(required=True)
    story_source.add_argument("--prompt-file")
    story_source.add_argument("--plan", help="Agent-authored story-plan JSON")
    story_parser.add_argument("-o", "--output-dir")
    story_parser.add_argument("--strategy", choices=["auto", "story", "dense", "visual"], default="auto")
    story_parser.add_argument("--mode", choices=["all", "outline-only", "prompts-only", "images-only"], default="all")
    story_parser.add_argument("--image", action="append", default=[], help="Attach an image; repeatable")
    story_parser.add_argument("--keep-svg", action="store_true")
    _add_dimensions(story_parser, story=True)
    _add_render_options(story_parser)

    assets_parser = subparsers.add_parser("assets", help="Generate OpenClaw thumbnail and icon assets")
    assets_parser.add_argument("project")
    asset_prompt = assets_parser.add_mutually_exclusive_group(required=True)
    asset_prompt.add_argument("--prompt")
    asset_prompt.add_argument("--prompt-file")
    assets_parser.add_argument("--keep-svg", action="store_true")

    validate_parser = subparsers.add_parser("validate-plan", help="Validate a story-plan JSON file")
    validate_parser.add_argument("plan")

    serve_parser = subparsers.add_parser("serve", help="Start the local HTTP service")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8787)

    return parser


def _run(args: argparse.Namespace) -> dict[str, Any] | None:
    if args.command == "create":
        return _run_create(args)

    if args.command == "generate":
        prompt = _read_prompt(args)
        suffix = ".svg" if args.format == "svg" else ".png"
        output = Path(args.output).expanduser() if args.output else default_output_path(prompt, suffix)
        if args.format == "svg":
            return write_svg(prompt, output, args.width, args.height, options=_render_options(args))
        return generate_image(
            prompt,
            output,
            args.width,
            args.height,
            svg_output=args.svg_output,
            keep_svg=args.keep_svg,
            options=_render_options(args),
        )

    if args.command == "story":
        if args.plan:
            plan = load_story_plan(args.plan)
            prompt = plan["title"]
        else:
            plan = None
            prompt = Path(args.prompt_file).expanduser().read_text(encoding="utf-8")
        output_dir = Path(args.output_dir).expanduser() if args.output_dir else default_story_dir(prompt)
        return generate_story(
            prompt,
            output_dir,
            args.width,
            args.height,
            strategy=args.strategy,
            mode=args.mode,
            story_images=args.image,
            story_plan=plan,
            keep_svg=args.keep_svg,
            options=_render_options(args),
        )

    if args.command == "assets":
        return generate_openclaw_assets(args.project, _read_prompt(args), keep_svg=args.keep_svg)

    if args.command == "validate-plan":
        plan = load_story_plan(args.plan)
        return {
            "valid": True,
            "path": str(Path(args.plan).expanduser().resolve()),
            "cards": len(plan["cards"]),
            "warnings": lint_story_plan(plan),
        }

    if args.command == "serve":
        from .service import serve

        serve(args.host, args.port)
        return None

    raise ValueError(f"unsupported command: {args.command}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = _run(args)
        if result is not None:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
