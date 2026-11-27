from __future__ import annotations
import json
import time
from pathlib import Path

_THEMES_FILE = "config/themes.json"


def _themes_path(root: Path) -> Path:
    return root / _THEMES_FILE


def load_all_themes(root: Path) -> list[dict]:
    p = _themes_path(root)
    if not p.exists():
        return []
    return json.loads(p.read_text())


def load_themes(root: Path) -> list[dict]:
    """Returns only enabled themes."""
    return [t for t in load_all_themes(root) if t.get("enabled", True)]


def save_themes(root: Path, themes: list[dict]) -> None:
    p = _themes_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(themes, indent=2))


def add_theme(root: Path, name: str, description: str, priority: str = "medium") -> dict:
    themes = load_all_themes(root)
    theme_id = f"theme_{int(time.time() * 1000) % 1_000_000:06d}"
    new_theme = {"id": theme_id, "name": name, "description": description, "enabled": True, "priority": priority}
    themes.append(new_theme)
    save_themes(root, themes)
    return new_theme


def update_theme(root: Path, theme_id: str, **kwargs) -> dict:
    themes = load_all_themes(root)
    for t in themes:
        if t["id"] == theme_id:
            allowed = {"name", "description", "priority", "enabled"}
            for k, v in kwargs.items():
                if k in allowed:
                    t[k] = v
            save_themes(root, themes)
            return t
    raise ValueError(f"Theme {theme_id} not found")


def delete_theme(root: Path, theme_id: str) -> bool:
    themes = load_all_themes(root)
    before = len(themes)
    themes = [t for t in themes if t["id"] != theme_id]
    if len(themes) == before:
        return False
    save_themes(root, themes)
    return True


def toggle_theme(root: Path, theme_id: str) -> dict:
    themes = load_all_themes(root)
    for t in themes:
        if t["id"] == theme_id:
            t["enabled"] = not t.get("enabled", True)
            save_themes(root, themes)
            return t
    raise ValueError(f"Theme {theme_id} not found")
