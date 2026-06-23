"""Start and stop the trading bot from the easy UI."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from easy_app.config import PROJECT_ROOT

STATUS_FILE = PROJECT_ROOT / ".bot_status.json"
RUNNER = PROJECT_ROOT / "5m_bot_runner.py"


def _read_status() -> Optional[Dict[str, Any]]:
    if not STATUS_FILE.exists():
        return None
    try:
        return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _write_status(data: Dict[str, Any]) -> None:
    STATUS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _clear_status() -> None:
    if STATUS_FILE.exists():
        STATUS_FILE.unlink()


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"],
            capture_output=True,
            text=True,
            check=False,
        )
        text = result.stdout or ""
        return str(pid) in text and "No tasks" not in text
    try:
        import os

        os.kill(pid, 0)
        return True
    except OSError:
        return False


def get_status() -> Dict[str, Any]:
    info = _read_status()
    if not info:
        return {"running": False}

    pid = int(info.get("pid", 0))
    if not _pid_alive(pid):
        _clear_status()
        return {"running": False}

    return {
        "running": True,
        "pid": pid,
        "live": bool(info.get("live")),
        "started_at": info.get("started_at"),
        "mode_label": "Live trading" if info.get("live") else "Practice (simulation)",
    }


def start_bot(*, live: bool) -> None:
    status = get_status()
    if status.get("running"):
        raise RuntimeError("Bot is already running. Stop it first.")

    if not RUNNER.exists():
        raise RuntimeError(f"Missing bot runner: {RUNNER.name}")

    args = [sys.executable, str(RUNNER)]
    if live:
        args.append("--live")

    popen_kwargs: Dict[str, Any] = {"cwd": str(PROJECT_ROOT)}
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True

    proc = subprocess.Popen(args, **popen_kwargs)

    _write_status(
        {
            "pid": proc.pid,
            "live": live,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
    )


def stop_bot() -> None:
    info = _read_status()
    if not info:
        return

    pid = int(info.get("pid", 0))
    if not _pid_alive(pid):
        _clear_status()
        return

    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            check=False,
        )
    else:
        import os
        import signal

        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        except ProcessLookupError:
            pass
        except OSError:
            os.kill(pid, signal.SIGTERM)

    _clear_status()
