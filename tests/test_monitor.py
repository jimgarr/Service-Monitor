from unittest import mock
"""Unit tests for the monitoring library."""

import os
import sys
import json

# Ensure the package can be imported when running tests directly on Windows
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from monitorlib.monitor import (
    Service,
    HealthResult,
    send_webhook_alert,
    check_services,
)

WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "http://example.com/webhook")


def test_send_webhook_alert():
    """send_webhook_alert posts a card with the expected structure."""

    with mock.patch("urllib.request.urlopen") as urlopen:
        urlopen.return_value.__enter__.return_value.read.return_value = b""
        with mock.patch("urllib.request.Request") as Request:
            send_webhook_alert(
                WEBHOOK_URL,
                {"service": {"message": "msg", "healthy": True}},
                ui_url="http://localhost:5000",
            )
            assert urlopen.called
            data = json.loads(Request.call_args[1]["data"].decode())
            card_body = data["body"]["attachments"][0]["content"]["body"]
            assert card_body[0]["text"] == "service"
            assert "Status: UP" in card_body[2]["text"]
            assert card_body[-1]["text"] == "[View details](http://localhost:5000)"


def test_check_services_alerts_on_conditions():
    """check_services passes through results and calls alert once."""

    service_ok = Service(
        "good_service",
        lambda: HealthResult(True, "ok"),
    )
    service_bad = Service("bad_service", lambda: HealthResult(False, "fail"))

    with mock.patch('monitorlib.monitor.send_webhook_alert') as alert:
        statuses = check_services([service_ok, service_bad], WEBHOOK_URL)
        assert statuses["good_service"]["healthy"] is True
        assert statuses["good_service"]["message"] == "ok"
        assert statuses["bad_service"]["healthy"] is False
        assert statuses["bad_service"]["message"] == "fail"
        alert.assert_called_once_with(WEBHOOK_URL, statuses, None)


def test_check_services_handles_exceptions():
    """A failing health check should result in an unhealthy status."""

    def bad():
        raise RuntimeError("boom")

    service = Service("explode", bad)

    with mock.patch("monitorlib.monitor.send_webhook_alert") as alert:
        statuses = check_services([service], WEBHOOK_URL)
        assert statuses["explode"]["healthy"] is False
        assert "boom" in statuses["explode"]["message"]
        alert.assert_called_once_with(WEBHOOK_URL, statuses, None)


def test_check_services_no_alert_when_all_ok():
    """When all services are healthy no alert is sent."""

    service1 = Service("svc1", lambda: HealthResult(True, "ok"))
    service2 = Service("svc2", lambda: HealthResult(True, "fine"))

    with mock.patch("monitorlib.monitor.send_webhook_alert") as alert:
        statuses = check_services([service1, service2], WEBHOOK_URL)
        assert statuses["svc1"]["healthy"] is True
        assert statuses["svc2"]["healthy"] is True
        alert.assert_not_called()


def test_check_services_with_mixed_outcomes():
    """Mixed healthy/unhealthy services produce one summary alert."""

    def ok():
        return HealthResult(True, "ok")

    def fail():
        return HealthResult(False, "fail")

    services = [
        Service("ok", ok),
        Service("fail", fail),
    ]

    with mock.patch("monitorlib.monitor.send_webhook_alert") as alert:
        statuses = check_services(services, WEBHOOK_URL)

    assert statuses["ok"]["healthy"] is True
    assert statuses["fail"]["healthy"] is False
    alert.assert_called_once_with(WEBHOOK_URL, statuses, None)


