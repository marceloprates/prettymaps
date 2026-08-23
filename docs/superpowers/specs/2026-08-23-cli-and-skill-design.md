# prettymaps CLI + global Claude skill

## Goal

Use prettymaps from the terminal and from any Claude Code project, without touching Python code by hand each time.

## Scope

1. A minimal CLI inside the `prettymaps` package.
2. A dedicated venv for the repo.
3. A global Claude Code skill that drives the CLI from any project.

## 1. CLI

New file `prettymaps/cli.py`, using `argparse` (stdlib, no new dependency).

Commands:

- `prettymaps plot QUERY [--preset NAME] [-o FILE] [--width N] [--height N]`
  Calls `prettymaps.plot(query, preset=preset, save_as=output, figsize=(width, height))`.
  Defaults: `preset="default"`, `-o` required, `--width`/`--height` default to the library default `(11.7, 11.7)` inches (native figsize units, no pixel conversion).
- `prettymaps list-presets`
  Prints one preset name per line from `prettymaps.presets()["preset"]`.

Errors (bad query, network failure, missing preset) propagate as-is — no custom retry/handling layer.

Entry point registered in `setup.py`:

```python
entry_points={"console_scripts": ["prettymaps=prettymaps.cli:main"]}
```

## 2. Environment

- `.venv` created inside the repo root (`python -m venv .venv`).
- `pip install -e .` run inside that venv, so `prettymaps` CLI is available as `.venv/Scripts/prettymaps.exe` (Windows) and importable for development.
- No global/system Python install touched.

## 3. Global Claude Code skill

- Location: `~/.claude/skills/prettymaps/SKILL.md` (global, available in every project).
- Trigger: user asks to generate/draw a map, mentions "prettymaps", or runs `/prettymaps`.
- Behavior: the skill's instructions tell Claude to invoke the CLI via Bash using the **absolute path** to the venv's Python/executable in this repo (e.g. `G:/Documenti/GitHub/prettymaps/.venv/Scripts/prettymaps.exe`), so it works regardless of the calling project's working directory or PATH.
- After generating a map, use `SendUserFile` to show the resulting image to the user.
- No wrapper scripts, no extra abstraction — the skill calls the CLI directly.

## Out of scope (explicitly not building)

- Pixel-based sizing (figsize stays in inches, matching the library's native API).
- Preset editing/creation from the CLI.
- Packaging/publishing prettymaps to PyPI.
- Any config file or settings layer for the skill.
