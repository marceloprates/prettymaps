# prettymaps CLI + Global Claude Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a minimal `prettymaps` CLI (`plot`, `list-presets`) installable via `pip install -e .`, and a global Claude Code skill that drives it from any project.

**Architecture:** `prettymaps/cli.py` wraps the existing `plot()`/`presets()` functions with `argparse`. `setup.py` registers a `prettymaps` console script pointing at `cli.main`. A dedicated `.venv` in the repo hosts the editable install. A skill file at `~/.claude/skills/prettymaps/SKILL.md` tells Claude to invoke the venv's `prettymaps` executable by absolute path from any project.

**Tech Stack:** Python 3.12, `argparse` (stdlib), existing `prettymaps` package, `pytest` for tests.

Spec: [`docs/superpowers/specs/2026-08-23-cli-and-skill-design.md`](../specs/2026-08-23-cli-and-skill-design.md)

---

### Task 1: Create the venv

**Files:** none (shell only)

- [ ] **Step 1: Create the venv**

Run: `python -m venv .venv`
Expected: creates `.venv/` in the repo root (already covered by `.gitignore`; verify with `git status` that nothing new is tracked).

- [ ] **Step 2: Install the package in editable mode**

Run (Windows Git Bash): `.venv/Scripts/python.exe -m pip install -e .`
Expected: installs `prettymaps` plus everything in `requirements.txt`. This takes a few minutes (rasterio/opencv/osmnx are large). No errors at the end.

- [ ] **Step 3: Install pytest into the venv**

Run: `.venv/Scripts/python.exe -m pip install pytest`
Expected: pytest installed, no errors.

---

### Task 2: CLI `plot` command

**Files:**
- Create: `prettymaps/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test for `plot` argument parsing and dispatch**

Create `tests/test_cli.py`:

```python
import prettymaps.cli as cli


def test_plot_command_calls_plot_with_parsed_args(monkeypatch):
    calls = []

    def fake_plot(query, preset=None, save_as=None, figsize=None):
        calls.append(
            {"query": query, "preset": preset, "save_as": save_as, "figsize": figsize}
        )

    monkeypatch.setattr(cli, "_plot", fake_plot)

    cli.main(["plot", "Bom Fim, Porto Alegre, Brasil", "-o", "out.png"])

    assert calls == [
        {
            "query": "Bom Fim, Porto Alegre, Brasil",
            "preset": "default",
            "save_as": "out.png",
            "figsize": (11.7, 11.7),
        }
    ]


def test_plot_command_with_preset_and_size(monkeypatch):
    calls = []

    def fake_plot(query, preset=None, save_as=None, figsize=None):
        calls.append(
            {"query": query, "preset": preset, "save_as": save_as, "figsize": figsize}
        )

    monkeypatch.setattr(cli, "_plot", fake_plot)

    cli.main(
        [
            "plot",
            "Rome, Italy",
            "--preset",
            "minimal",
            "-o",
            "rome.svg",
            "--width",
            "8",
            "--height",
            "10",
        ]
    )

    assert calls == [
        {
            "query": "Rome, Italy",
            "preset": "minimal",
            "save_as": "rome.svg",
            "figsize": (8.0, 10.0),
        }
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_cli.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'prettymaps.cli'`

- [ ] **Step 3: Write minimal implementation**

Create `prettymaps/cli.py`:

```python
import argparse

from .draw import plot as _plot
from .draw import presets as _presets


def build_parser():
    parser = argparse.ArgumentParser(prog="prettymaps")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plot_parser = subparsers.add_parser("plot", help="Draw a map for a query")
    plot_parser.add_argument("query", help="Place name, coordinates, or address")
    plot_parser.add_argument(
        "--preset", default="default", help="Preset name (see list-presets)"
    )
    plot_parser.add_argument(
        "-o", "--output", required=True, help="Output file path (e.g. map.png)"
    )
    plot_parser.add_argument(
        "--width", type=float, default=11.7, help="Figure width in inches"
    )
    plot_parser.add_argument(
        "--height", type=float, default=11.7, help="Figure height in inches"
    )

    subparsers.add_parser("list-presets", help="List available preset names")

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.command == "plot":
        _plot(
            args.query,
            preset=args.preset,
            save_as=args.output,
            figsize=(args.width, args.height),
        )
    elif args.command == "list-presets":
        for name in _presets()["preset"]:
            print(name)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_cli.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git checkout -b add-prettymaps-cli
git add prettymaps/cli.py tests/test_cli.py
git commit -m "feat: add prettymaps plot CLI command"
```

---

### Task 3: CLI `list-presets` command

**Files:**
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_cli.py`:

```python
def test_list_presets_prints_preset_names(capsys):
    cli.main(["list-presets"])

    out = capsys.readouterr().out
    assert "default" in out.splitlines()
```

- [ ] **Step 2: Run test to verify it fails or passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_cli.py::test_list_presets_prints_preset_names -v`
Expected: PASS already, since `list-presets` was implemented together with the parser in Task 2. This step exists to lock in the behavior with a dedicated test — if it fails, the `list-presets` branch in `main()` has a bug; re-check the `elif args.command == "list-presets":` block in `prettymaps/cli.py`.

- [ ] **Step 3: Run the full CLI test file**

Run: `.venv/Scripts/python.exe -m pytest tests/test_cli.py -v`
Expected: PASS (3 tests)

- [ ] **Step 4: Commit**

```bash
git add tests/test_cli.py
git commit -m "test: lock in list-presets CLI output"
```

---

### Task 4: Register console script and verify end-to-end

**Files:**
- Modify: `setup.py`

- [ ] **Step 1: Add the entry point**

In `setup.py`, add `entry_points` to the `setup()` call (after `package_data`):

```python
    package_data={"prettymaps": ["presets/*.json"]},
    entry_points={"console_scripts": ["prettymaps=prettymaps.cli:main"]},
    python_requires=">=3.12",
```

- [ ] **Step 2: Reinstall editable to pick up the entry point**

Run: `.venv/Scripts/python.exe -m pip install -e .`
Expected: reinstalls, creates `.venv/Scripts/prettymaps.exe`

- [ ] **Step 3: Verify the console script works**

Run: `.venv/Scripts/prettymaps.exe list-presets`
Expected: prints one preset name per line, including `default`

- [ ] **Step 4: Verify plot end-to-end against a real query (manual, network-dependent)**

Run: `.venv/Scripts/prettymaps.exe plot "Bom Fim, Porto Alegre, Brasil" -o /tmp/test-map.png`
Expected: no errors, `/tmp/test-map.png` exists and is a non-empty PNG. This hits OpenStreetMap over the network — same as the existing tests in `tests/test.py`, no mocking.

- [ ] **Step 5: Commit**

```bash
git add setup.py
git commit -m "feat: register prettymaps console script"
```

---

### Task 5: Global Claude Code skill

**Files:**
- Create: `C:\Users\tomma\.claude\skills\prettymaps\SKILL.md`

- [ ] **Step 1: Write the skill file**

Create `C:\Users\tomma\.claude\skills\prettymaps\SKILL.md`:

```markdown
---
name: prettymaps
description: Generate a decorative map (PNG/SVG) for a place using the local prettymaps CLI. Use when the user asks to draw, generate, or create a map, a city map poster, or mentions prettymaps.
---

# prettymaps

Generates pretty maps from OpenStreetMap data via the local `prettymaps` CLI,
installed in a dedicated venv inside the `prettymaps` repo.

## Running the CLI

Always call the CLI by its absolute path — this works regardless of the
calling project's working directory or PATH:

```
G:/Documenti/GitHub/prettymaps/.venv/Scripts/prettymaps.exe <command> ...
```

## Commands

- `list-presets` — prints available preset names.
- `plot QUERY -o OUTPUT [--preset NAME] [--width N] [--height N]` — draws a
  map for `QUERY` (a place name, address, or "lat, lon") and saves it to
  `OUTPUT` (extension controls format, e.g. `.png`, `.svg`). `--preset`
  defaults to `default`; run `list-presets` first if the user names a style
  you're unsure about. `--width`/`--height` are in inches, default 11.7x11.7.

## Workflow

1. Ask the user for the place/query if not given.
2. Pick an output path (scratchpad directory if the user doesn't specify one).
3. Run the `plot` command via Bash using the absolute path above.
4. Send the resulting image to the user with `SendUserFile`.

## Example

```bash
G:/Documenti/GitHub/prettymaps/.venv/Scripts/prettymaps.exe plot "Rome, Italy" -o rome.png --preset default
```
```

- [ ] **Step 2: Verify the skill is picked up**

Run (from any directory, in a new Claude Code session): ask "generate a prettymaps map of Rome" and confirm Claude invokes the skill and calls the CLI by absolute path.
Expected: the skill triggers, the CLI runs, an image file is produced and sent back.

- [ ] **Step 3: Commit the plan/skill reference in the repo (optional doc trail)**

No repo file changes are required for this task since the skill lives outside the repo in `~/.claude/skills/`. Nothing to commit here.

---

## Self-Review Notes

- Spec coverage: CLI `plot`/`list-presets` (Tasks 2-3), venv (Task 1), console-script install (Task 4), global skill (Task 5) — all spec sections covered.
- Out-of-scope items from the spec (pixel sizing, preset editing, PyPI publishing, skill config layer) are intentionally not tasked.
- `_plot`/`_presets` names in `cli.py` are used consistently between Task 2's implementation and its tests.
