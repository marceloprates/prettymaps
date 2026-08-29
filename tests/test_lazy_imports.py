"""Lazy optional deps (#157) and python_requires pin (#156)."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _top_level_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return names


def test_draw_does_not_top_level_import_optional_heavy_deps():
    names = _top_level_imports(ROOT / "prettymaps" / "draw.py")
    for banned in ("cv2", "vsketch", "thefuzz", "sklearn"):
        assert banned not in names, f"{banned} still imported at top level in draw.py"


def test_fetch_does_not_top_level_import_elevation_stack():
    names = _top_level_imports(ROOT / "prettymaps" / "fetch.py")
    for banned in ("elevation", "rioxarray", "rasterio", "skimage", "IPython"):
        assert banned not in names, f"{banned} still imported at top level in fetch.py"


def test_python_requires_matches_vsketch_window():
    setup = (ROOT / "setup.py").read_text(encoding="utf-8")
    assert 'python_requires=">=3.12,<3.14"' in setup


def test_lazy_import_error_messages_present():
    draw = (ROOT / "prettymaps" / "draw.py").read_text(encoding="utf-8")
    fetch = (ROOT / "prettymaps" / "fetch.py").read_text(encoding="utf-8")
    assert "opencv-python-headless" in draw
    assert "pip install vsketch" in draw
    assert "pip install thefuzz" in draw
    assert "elevation, rioxarray, and rasterio" in fetch
    assert "scikit-image" in fetch
