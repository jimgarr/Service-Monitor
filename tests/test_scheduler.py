from unittest import mock
import sys
import types
import time
import os

WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "http://example.com/webhook")

# Provide minimal requests module so scheduler can be imported
sys.modules['requests'] = types.SimpleNamespace(post=lambda *a, **k: None)

import scheduler
import monitorlib.monitor as monitor


def _run_scheduler(fn):
    scheduler.requests.post = lambda *a, **k: None
    scheduler.add_test("svc", fn, 60)
    scheduler.start_test("svc")
    time.sleep(0.05)
    scheduler.stop_all()
    t = scheduler._tests["svc"].thread
    if t:
        t.join()
    scheduler._tests.clear()
    scheduler._results.clear()


def test_scheduler_no_webhook_on_success():
    """Healthy scheduled runs should not trigger webhook notifications."""

    def health():
        return monitor.HealthResult(True, "ok")

    def run_check():
        monitor.check_services([monitor.Service("svc", health)], WEBHOOK_URL)

    with mock.patch("monitorlib.monitor.send_webhook_alert") as alert:
        _run_scheduler(run_check)
    alert.assert_not_called()


def test_scheduler_triggers_webhook_on_failure():
    """Unhealthy scheduled runs should trigger a webhook notification."""

    def health():
        return monitor.HealthResult(False, "fail")

    def run_check():
        monitor.check_services([monitor.Service("svc", health)], WEBHOOK_URL)

    with mock.patch("monitorlib.monitor.send_webhook_alert") as alert:
        _run_scheduler(run_check)
    alert.assert_called_once()
