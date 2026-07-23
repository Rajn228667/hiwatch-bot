"""JSON store: managers chat_ids + chat history."""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

_DATA = Path(__file__).resolve().parent.parent / "data" / "store.json"
_LOCK = Lock()


def _load() -> dict:
    if not _DATA.exists():
        return {"admin_chat_ids": [], "admin_chat_id": None, "history": {}}
    try:
        return json.loads(_DATA.read_text(encoding="utf-8"))
    except Exception:
        return {"admin_chat_ids": [], "admin_chat_id": None, "history": {}}


def _save(data: dict) -> None:
    _DATA.parent.mkdir(parents=True, exist_ok=True)
    _DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_admin_ids() -> list[int]:
    """Все chat_id менеджеров (уникальные)."""
    with _LOCK:
        d = _load()
        ids: list[int] = []
        raw = d.get("admin_chat_ids") or []
        for x in raw:
            try:
                ids.append(int(x))
            except (TypeError, ValueError):
                pass
        # legacy single field
        legacy = d.get("admin_chat_id")
        if legacy:
            try:
                ids.append(int(legacy))
            except (TypeError, ValueError):
                pass
        # unique preserve order
        seen: set[int] = set()
        out: list[int] = []
        for i in ids:
            if i not in seen:
                seen.add(i)
                out.append(i)
        return out


def get_admin_id() -> int | None:
    ids = get_admin_ids()
    return ids[0] if ids else None


def set_admin_id(chat_id: int) -> None:
    """Добавить менеджера (не затирает остальных)."""
    add_admin_id(chat_id)


def add_admin_id(chat_id: int) -> list[int]:
    with _LOCK:
        d = _load()
        ids = [int(x) for x in (d.get("admin_chat_ids") or []) if str(x).lstrip("-").isdigit()]
        cid = int(chat_id)
        if cid not in ids:
            ids.append(cid)
        d["admin_chat_ids"] = ids
        d["admin_chat_id"] = cid  # legacy
        _save(d)
        return list(ids)


def remove_admin_id(chat_id: int) -> list[int]:
    with _LOCK:
        d = _load()
        cid = int(chat_id)
        ids = [int(x) for x in (d.get("admin_chat_ids") or []) if int(x) != cid]
        d["admin_chat_ids"] = ids
        d["admin_chat_id"] = ids[0] if ids else None
        _save(d)
        return list(ids)


def push_history(user_id: int, role: str, content: str, limit: int = 8) -> list[dict]:
    with _LOCK:
        d = _load()
        hist = d.setdefault("history", {})
        key = str(user_id)
        arr = hist.get(key, [])
        arr.append({"role": role, "content": content})
        arr = arr[-limit:]
        # не раздувать файл: максимум 200 чатов
        if len(hist) > 200:
            # drop oldest keys (simple)
            for k in list(hist.keys())[: len(hist) - 200]:
                if k != key:
                    del hist[k]
        hist[key] = arr
        _save(d)
        return list(arr)
