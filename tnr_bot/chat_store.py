"""
Persist Telegram user id by normalized @handle so the notify HTTP process can resolve
chat_id without Airtable writes (bot and uvicorn share the same file on one machine).

Set TELEGRAM_CHAT_STORE_PATH to an absolute path if bot and notify run from different cwd.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_lock = threading.Lock()

_DEFAULT_NAME = ".telegram_chat_store.json"


def _store_path() -> Path:
    raw = os.getenv("TELEGRAM_CHAT_STORE_PATH", "").strip()
    if raw:
        return Path(raw).expanduser()
    return Path.cwd() / _DEFAULT_NAME


def _read_all() -> dict[str, Any]:
    path = _store_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Could not read chat store %s: %s", path, e)
        return {}


def _write_all(data: dict[str, Any]) -> None:
    path = _store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    text = json.dumps(data, ensure_ascii=False, indent=0, sort_keys=True)
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def remember_chat_id(normalized_handle: str, chat_id: int) -> None:
    """Upsert mapping for LOWERCASE normalized handle (no @)."""
    key = normalized_handle.strip().lower()
    if not key:
        return
    with _lock:
        data = _read_all()
        data[key] = int(chat_id)
        _write_all(data)


def get_remembered_chat_id(normalized_handle: str) -> int | None:
    key = normalized_handle.strip().lower()
    if not key:
        return None
    with _lock:
        data = _read_all()
        raw = data.get(key)
        if raw is None:
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None
