from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .api import (
    generate_image,
    generate_openclaw_assets,
    generate_story,
    validate_story_plan,
)

MAX_BODY_BYTES = 2 * 1024 * 1024


class Handler(BaseHTTPRequestHandler):
    server_version = "FreeImageGenHTTP/2.0"

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _read_payload(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_BODY_BYTES:
            raise ValueError("request body is too large")
        raw = self.rfile.read(length) if length else b"{}"
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("JSON body must be an object")
        return payload

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._send_json(200, {"ok": True})

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send_json(200, {"ok": True, "service": "free-imagegen"})
            return
        self._send_json(404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        try:
            payload = self._read_payload()
            result = self._dispatch(payload)
            self._send_json(200, {"ok": True, "result": result})
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            self._send_json(400, {"ok": False, "error": str(exc)})
        except (OSError, RuntimeError) as exc:
            self._send_json(500, {"ok": False, "error": str(exc)})

    def _dispatch(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.path == "/generate":
            prompt = str(payload.get("prompt", "")).strip()
            output = str(payload.get("output", "")).strip()
            if not prompt or not output:
                raise ValueError("fields 'prompt' and 'output' are required")
            return generate_image(
                prompt,
                output,
                int(payload.get("width", 1024)),
                int(payload.get("height", 1024)),
                keep_svg=bool(payload.get("keep_svg", False)),
            )

        if self.path == "/story":
            prompt = str(payload.get("prompt", "")).strip()
            output_dir = str(payload.get("output_dir", "")).strip()
            plan = payload.get("plan")
            if plan is not None:
                plan = validate_story_plan(plan)
                prompt = prompt or plan["title"]
            if not prompt or not output_dir:
                raise ValueError("fields 'prompt'/'plan' and 'output_dir' are required")
            return generate_story(
                prompt,
                output_dir,
                int(payload.get("width", 1080)),
                int(payload.get("height", 1440)),
                strategy=str(payload.get("strategy", "auto")),
                mode=str(payload.get("mode", "all")),
                story_images=[str(item) for item in payload.get("images", [])],
                story_plan=plan,
                keep_svg=bool(payload.get("keep_svg", False)),
            )

        if self.path == "/assets":
            prompt = str(payload.get("prompt", "")).strip()
            project = str(payload.get("project", "")).strip()
            if not prompt or not project:
                raise ValueError("fields 'prompt' and 'project' are required")
            return generate_openclaw_assets(
                project, prompt, keep_svg=bool(payload.get("keep_svg", False))
            )

        if self.path == "/validate-plan":
            plan = validate_story_plan(payload.get("plan"))
            return {"valid": True, "cards": len(plan["cards"])}

        raise ValueError(f"unknown endpoint: {self.path}")


def serve(host: str = "127.0.0.1", port: int = 8787) -> None:
    if not 1 <= port <= 65535:
        raise ValueError("port must be between 1 and 65535")
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Serving Free ImageGen on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
