---
name: free-imagegen
description: Generate local SVG or PNG covers, infographics, article card sets, and OpenClaw assets through the installed free-imagegen CLI. Use when image output must stay local and does not require photorealistic diffusion.
---

# Free ImageGen

Use the installed `free-imagegen` command as the rendering boundary.

## Workflow

1. Choose `generate` for one image, `story` for an article/card set, or `assets` for OpenClaw assets.
2. Prefer SVG output when no local PNG renderer is available.
3. For article workflows, read the source first and create a story plan when pagination or page-type judgment matters.
4. Validate a plan with `free-imagegen validate-plan <file>` before rendering.
5. Keep titles short and body copy mobile-readable.

## Commands

```bash
free-imagegen generate --prompt "text cover, title Local First" --format svg --output output.svg
free-imagegen story --plan story-plan.json --output-dir output/story
free-imagegen assets /path/to/project --prompt "arcade game"
```

Read the installed package's `resources/story-plan.guide.md` and schema when authoring a story plan.
