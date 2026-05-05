from __future__ import annotations

import json
import os
import sys
from typing import Any

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TOOLS = os.path.join(ROOT, "tools")

if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)


def state_file(name: str) -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, "Adi", name)


def load_json_state(name: str) -> dict[str, Any]:
    try:
        with open(state_file(name), "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_json_state(name: str, state: dict[str, Any]) -> None:
    try:
        path = state_file(name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def default_examples_dir() -> str:
    return os.path.join(ROOT, "examples", "bija")


def load_last_sutra_dir(state_name: str) -> str:
    state = load_json_state(state_name)
    path = state.get("last_sutra_dir", "")
    if isinstance(path, str) and os.path.isdir(path):
        return path
    return default_examples_dir()


def save_last_sutra_dir(state_name: str, path: str) -> None:
    if not path:
        return
    state = load_json_state(state_name)
    state["last_sutra_dir"] = path
    save_json_state(state_name, state)


def resolve_repo_path(path: str | None, default_relative: str) -> str:
    text = (path or "").strip()
    if not text:
        text = default_relative
    return text if os.path.isabs(text) else os.path.join(ROOT, text)


def as_repo_path(path: str) -> str:
    try:
        return os.path.relpath(path, ROOT)
    except ValueError:
        return path
