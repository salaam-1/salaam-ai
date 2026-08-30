"""
Salaam's persistent brain.

A tiny JSON-file store so that facts, notes and reminders survive a restart.
Deliberately dependency-free — one small file per collection under
``config.DATA_DIR`` (defaults to ``~/.salaam``).
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from datetime import datetime, timezone
from typing import Any

from salaam.config import config

_LOCK = threading.Lock()


def _path(collection: str) -> str:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    return str(config.DATA_DIR / f"{collection}.json")


def load(collection: str) -> list[dict[str, Any]]:
    """Read a collection. Returns [] if it doesn't exist or is corrupt."""
    try:
        with open(_path(collection), "r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []


def save(collection: str, rows: list[dict[str, Any]]) -> None:
    """Write a collection atomically so a crash can't truncate the file."""
    target = _path(collection)
    directory = os.path.dirname(target)
    handle, temp_path = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as file:
            json.dump(rows, file, indent=2, ensure_ascii=False)
        os.replace(temp_path, target)
    except BaseException:
        # Never leave a stray temp file behind if the write blew up.
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def append(collection: str, row: dict[str, Any]) -> dict[str, Any]:
    """Add one row, stamping it with an id and creation time."""
    with _LOCK:
        rows = load(collection)
        row = {
            "id": _next_id(rows),
            "created_at": now_iso(),
            **row,
        }
        rows.append(row)
        save(collection, rows)
    return row


def remove(collection: str, row_id: int) -> dict[str, Any] | None:
    """Delete one row by id. Returns the removed row, or None if absent."""
    with _LOCK:
        rows = load(collection)
        for index, row in enumerate(rows):
            if row.get("id") == row_id:
                removed = rows.pop(index)
                save(collection, rows)
                return removed
    return None


def update(collection: str, row_id: int, **fields: Any) -> dict[str, Any] | None:
    """Patch fields on one row by id."""
    with _LOCK:
        rows = load(collection)
        for row in rows:
            if row.get("id") == row_id:
                row.update(fields)
                save(collection, rows)
                return row
    return None


def _next_id(rows: list[dict[str, Any]]) -> int:
    return max((int(row.get("id", 0)) for row in rows), default=0) + 1


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
