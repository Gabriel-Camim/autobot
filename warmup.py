from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional

from config import Settings


_lock = threading.Lock()
_status: Dict[str, Any] = {
    "state": "idle",
    "started_at": None,
    "finished_at": None,
    "duration_ms": None,
    "error": None,
}


def warmup_status() -> Dict[str, Any]:
    return dict(_status)


def _set_status(**values: Any) -> None:
    _status.update(values)


def _run(settings: Settings, actor: Optional[str] = None) -> None:
    started = time.time()
    try:
        from agent import warm_rag

        details = warm_rag(settings)
        _set_status(
            state="success",
            finished_at=time.time(),
            duration_ms=int((time.time() - started) * 1000),
            error=None,
            details=details,
            actor=actor,
        )
    except Exception as exc:
        _set_status(
            state="error",
            finished_at=time.time(),
            duration_ms=int((time.time() - started) * 1000),
            error=str(exc)[:240],
            actor=actor,
        )
    finally:
        _lock.release()


def start_warmup(settings: Settings, actor: Optional[str] = None) -> Dict[str, Any]:
    if not _lock.acquire(blocking=False):
        return warmup_status()
    _set_status(
        state="running",
        started_at=time.time(),
        finished_at=None,
        duration_ms=None,
        error=None,
        actor=actor,
    )
    thread = threading.Thread(target=_run, args=(settings, actor), daemon=True)
    thread.start()
    return warmup_status()
