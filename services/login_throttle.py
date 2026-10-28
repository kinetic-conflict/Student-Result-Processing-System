"""In-memory limit on failed logins.

State lives in this process only: it resets when the app restarts and is not
shared between worker processes. That fits the single-process local setup this
project targets; a multi-worker deployment would need a shared store.
"""
import threading
import time
from collections import deque

PURGE_THRESHOLD = 1000


class LoginThrottle:
    def __init__(self, max_failures=5, window_seconds=900, clock=time.monotonic):
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self._clock = clock
        self._failures = {}
        self._lock = threading.Lock()

    def _recent(self, key, now):
        failures = self._failures.get(key)
        if failures is None:
            return None
        while failures and now - failures[0] > self.window_seconds:
            failures.popleft()
        if not failures:
            del self._failures[key]
            return None
        return failures

    def is_blocked(self, key):
        with self._lock:
            failures = self._recent(key, self._clock())
            return failures is not None and len(failures) >= self.max_failures

    def record_failure(self, key):
        with self._lock:
            now = self._clock()
            if len(self._failures) > PURGE_THRESHOLD:
                for stale in list(self._failures):
                    self._recent(stale, now)
            self._failures.setdefault(key, deque()).append(now)

    def reset(self, key):
        with self._lock:
            self._failures.pop(key, None)
