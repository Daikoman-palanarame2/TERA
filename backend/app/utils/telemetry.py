"""
Module: backend/app/utils/telemetry
Purpose:
    Implements TelemetryLogger to write telemetry records atomically using file locks.
"""

import os
import json
import threading
from typing import Any
from app.schemas.data_contracts import TelemetryLog

try:
    import msvcrt
except ImportError:
    msvcrt = None  # type: ignore

try:
    import fcntl
except ImportError:
    fcntl = None  # type: ignore

msvcrt_any: Any = msvcrt
fcntl_any: Any = fcntl


def lock_file(f: Any) -> None:
    """Apply exclusive file lock."""
    if fcntl_any:
        try:
            fcntl_any.flock(f.fileno(), fcntl_any.LOCK_EX)
        except OSError:
            pass
    elif msvcrt_any:
        try:
            msvcrt_any.locking(f.fileno(), msvcrt_any.LK_LOCK, 1)
        except OSError:
            pass


def unlock_file(f: Any) -> None:
    """Release file lock."""
    if fcntl_any:
        try:
            fcntl_any.flock(f.fileno(), fcntl_any.LOCK_UN)
        except OSError:
            pass
    elif msvcrt_any:
        try:
            msvcrt_any.locking(f.fileno(), msvcrt_any.LK_UNLCK, 1)
        except OSError:
            pass


class TelemetryLogger:
    """Atomic file logger for transaction telemetry records."""

    def __init__(self, file_path: str) -> None:
        """Bind to output JSON file path."""
        self.file_path = file_path
        self.lock = threading.Lock()
        
        # Ensure target directory exists
        dir_name = os.path.dirname(file_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

    def log_metrics(self, entry: TelemetryLog) -> None:
        """Append log record atomically utilizing file locks."""
        data = entry.model_dump()
        line = json.dumps(data) + "\n"
        
        with self.lock:
            try:
                # Open in append mode
                with open(self.file_path, "a", encoding="utf-8") as f:
                    lock_file(f)
                    f.write(line)
                    f.flush()
                    unlock_file(f)
            except Exception as e:
                import logging
                logging.getLogger("tera_core").error(f"Failed to write telemetry: {e}")
