"""Simple scheduling manager for running health checks on intervals."""

from dataclasses import dataclass
import threading
import time
from typing import Callable, Dict, Optional
import os
import requests
import logging

from monitorlib.monitor import HealthResult

logger = logging.getLogger(__name__)


@dataclass
class ScheduledTest:
    """Represents a single scheduled health check."""

    fn: Callable[[], HealthResult]
    interval: float
    running: bool = False
    thread: Optional[threading.Thread] = None
    last_result: Optional[HealthResult] = None


_tests: Dict[str, ScheduledTest] = {}
_results: Dict[str, Dict[str, str]] = {}

# Optional integration endpoints
_ui_url: Optional[str] = os.environ.get("UI_URL")


def add_test(name: str, fn: Callable[[], HealthResult], interval: float) -> None:
    """Register or replace a health check to run periodically."""
    existing = _tests.get(name)
    if existing:
        # Stop any running thread before replacing the test
        stop_test(name)
        if existing.thread and existing.thread.is_alive():
            existing.thread.join()
    _tests[name] = ScheduledTest(fn=fn, interval=interval)


def _post_results() -> None:
    logger.info("_post_results called")
    if not _results:
        return
    if _ui_url:
        try:
            requests.post(
                f"{_ui_url}/results",
                json={"results": _results, "error": None},
                timeout=2,
            )
        except Exception:
            pass


def _run(name: str) -> None:
    test = _tests[name]
    while test.running:
        start = time.time()
        try:
            res = test.fn()
        except Exception as exc:  # safety net
            res = HealthResult(False, str(exc))

        if isinstance(res, HealthResult):
            test.last_result = res
            _results[name] = {"healthy": res.healthy, "message": res.message}
            _post_results()
        elapsed = time.time() - start
        wait_time = max(0, test.interval - elapsed)
        time.sleep(wait_time)


def start_test(name: str) -> None:
    """Start running the named test in its own thread."""
    test = _tests.get(name)
    if not test or test.running:
        return
    test.running = True
    t = threading.Thread(target=_run, args=(name,), daemon=True)
    test.thread = t
    t.start()


def stop_test(name: str) -> None:
    """Stop the named test."""
    test = _tests.get(name)
    if not test:
        return
    test.running = False


def _restart_test(name: str) -> None:
    """Cancel and restart the thread for the given test if running."""
    test = _tests.get(name)
    if not test or not test.running:
        return
    stop_test(name)
    if test.thread and test.thread.is_alive():
        test.thread.join()
    start_test(name)


def set_interval(name: str, seconds: float) -> None:
    """Update the interval for a running test."""
    test = _tests.get(name)
    if test:
        test.interval = seconds
        if test.running:
            _restart_test(name)


def start_all() -> None:
    """Start all registered tests."""
    for name in list(_tests.keys()):
        start_test(name)


def stop_all() -> None:
    """Stop all running tests."""
    for name in list(_tests.keys()):
        stop_test(name)


def any_running() -> bool:
    """Return True if any scheduled test is currently running."""
    return any(t.running for t in _tests.values())


def get_min_interval() -> Optional[float]:
    """Return the smallest interval among running tests, if any.

    If no tests are running, ``None`` is returned.
    """
    intervals = [t.interval for t in _tests.values() if t.running]
    if not intervals:
        return None
    return min(intervals)


