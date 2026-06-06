"""LLM client for generating structured prompts and story plans via OpenAI-compatible API."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from openai import OpenAI

from .llm_prompts import STORY_PLAN_SYSTEM, STRUCTURED_PROMPT_SYSTEM

_ENV_KEYS = (
    "BASE_URL",
    "MODEL",
    "API_KEY",
    "TEMPERATURE",
    "MAX_TOKENS",
    "TIMEOUT",
    "MAX_RETRIES",
)


def _find_env_file() -> Path | None:
    """Find .env file by walking up from CWD."""
    cwd = Path.cwd()
    for _ in range(10):
        candidate = cwd / ".env"
        if candidate.is_file():
            return candidate
        parent = cwd.parent
        if parent == cwd:
            break
        cwd = parent
    return None


def _parse_env_file(path: Path) -> dict[str, str]:
    """Parse a simple KEY=VALUE .env file."""
    env: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        # Strip matching quotes
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if value:
            env[key] = value
    return env


def _load_env() -> dict[str, str]:
    """Load .env file values. Environment variables take precedence."""
    env: dict[str, str] = {}
    env_path = _find_env_file()
    if env_path is not None:
        env = _parse_env_file(env_path)
    # os.environ overrides .env
    for key in _ENV_KEYS:
        if key in os.environ:
            env[key] = os.environ[key]
    return env


def _get_llm_config() -> dict[str, Any]:
    """Get LLM configuration from .env / environment."""
    env = _load_env()
    base_url = env.get("BASE_URL", "")
    model = env.get("MODEL", "")
    api_key = env.get("API_KEY", "")

    if not base_url:
        raise RuntimeError(
            "BASE_URL not configured. Set it in .env or environment variable."
        )
    if not model:
        raise RuntimeError(
            "MODEL not configured. Set it in .env or environment variable."
        )
    if not api_key:
        raise RuntimeError(
            "API_KEY not configured. Set it in .env or environment variable."
        )

    return {
        "base_url": base_url,
        "model": model,
        "api_key": api_key,
        "temperature": float(env.get("TEMPERATURE", "0.7")),
        "max_tokens": int(env.get("MAX_TOKENS", "4096")),
        "timeout": float(env.get("TIMEOUT", "90")),
        "max_retries": int(env.get("MAX_RETRIES", "3")),
    }


def _print_status(msg: str) -> None:
    """Print a status message to stderr so it doesn't pollute JSON output."""
    print(f"[llm] {msg}", file=sys.stderr, flush=True)


def call_llm(system_prompt: str, user_prompt: str) -> str:
    """Call the LLM via OpenAI-compatible API and return the response text."""
    config = _get_llm_config()
    client = OpenAI(
        base_url=config["base_url"],
        api_key=config["api_key"],
        timeout=config["timeout"],
        max_retries=config["max_retries"],
    )
    _print_status(f"Calling {config['model']} ...")
    response = client.chat.completions.create(
        model=config["model"],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=config["temperature"],
        max_tokens=config["max_tokens"],
    )
    content = response.choices[0].message.content or ""
    _print_status(f"LLM responded ({len(content)} chars)")
    return content.strip()


def generate_structured_prompt(idea: str) -> str:
    """Use LLM to convert a simple idea into a structured prompt for the rendering engine."""
    _print_status(f"Generating structured prompt for: {idea}")
    prompt = call_llm(STRUCTURED_PROMPT_SYSTEM, idea)
    # Clean up: remove markdown code blocks if present
    prompt = re.sub(r"^```\w*\n?", "", prompt)
    prompt = re.sub(r"\n?```$", "", prompt)
    return prompt.strip()


def _extract_json(text: str) -> str:
    """Extract JSON from LLM output, handling markdown code blocks."""
    # Try to find JSON in markdown code block
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Try the whole text as JSON
    text = text.strip()
    if text.startswith("{"):
        return text
    # Try to find first { ... } pair
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        return text[start : end + 1]
    return text


def generate_story_plan(idea: str, num_cards: int | None = None) -> dict[str, Any]:
    """Use LLM to generate a story-plan JSON from a simple idea."""
    from .api import validate_story_plan

    user_prompt = idea
    if num_cards is not None:
        user_prompt = f"{idea}\n\n请生成恰好 {num_cards} 张卡片。"

    _print_status(f"Generating story plan for: {idea}")
    raw = call_llm(STORY_PLAN_SYSTEM, user_prompt)
    json_str = _extract_json(raw)

    try:
        plan = json.loads(json_str)
    except json.JSONDecodeError as exc:
        _print_status(f"LLM output is not valid JSON: {exc}")
        _print_status(f"Raw output:\n{raw[:500]}")
        raise ValueError(f"LLM did not return valid JSON: {exc}") from exc

    if not isinstance(plan, dict):
        raise ValueError("LLM did not return a JSON object")

    # Validate using the existing engine validator
    plan = validate_story_plan(plan)
    _print_status(f"Story plan validated: {len(plan.get('cards', []))} cards")
    return plan
