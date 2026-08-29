import threading
from datetime import datetime, timezone
from typing import Optional


class KillSwitch:
    """富邦交易緊急熔斷開關 (線程安全)"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._is_active = False
                cls._instance._reason = None
                cls._instance._activated_at = None
        return cls._instance

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def reason(self) -> Optional[str]:
        return self._reason

    @property
    def activated_at(self) -> Optional[str]:
        return self._activated_at

    def activate(self, reason: str):
        with self._lock:
            self._is_active = True
            self._reason = reason
            self._activated_at = datetime.now(timezone.utc).isoformat()

    def reset(self):
        with self._lock:
            self._is_active = False
            self._reason = None
            self._activated_at = None
