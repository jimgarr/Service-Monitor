import sys
import types
from unittest import mock

class _FakeRequest:
    def __init__(self):
        self.form = {}
        self._json = {}

    def get_json(self, force=False):
        return self._json

fake_request = _FakeRequest()

class _FakeFlask:
    def __init__(self, *args, **kwargs):
        pass

    def route(self, *args, **kwargs):
        def decorator(fn):
            return fn
        return decorator

    def test_client(self):
        class Client:
            def post(self, path, data=None):
                fake_request.form = data or {}
                if path == '/start_all_schedulers':
                    return types.SimpleNamespace(status_code=302, data=ui_server.start_all_schedulers())
                if path == '/stop_scheduler':
                    return types.SimpleNamespace(status_code=302, data=ui_server.stop_scheduler())
                if path == '/run_login_once':
                    return types.SimpleNamespace(status_code=302, data=ui_server.run_login_once())
        return Client()

def fake_redirect(url):
    return url

def fake_url_for(name):
    return name

sys.modules['flask'] = types.SimpleNamespace(
    Flask=_FakeFlask,
    request=fake_request,
    redirect=fake_redirect,
    url_for=fake_url_for,
    render_template=lambda *a, **k: "",
)

import ui_server


def test_start_all_schedulers_schedules_login_job():
    with mock.patch('ui_server.scheduler.add_test') as add_test, \
         mock.patch('ui_server.scheduler.start_test') as start_test:
        client = ui_server.app.test_client()
        response = client.post('/start_all_schedulers', data={'interval_login': '5'})

        assert response.status_code == 302
        add_test.assert_called_once_with('login_check', ui_server.trigger_login_check, 5.0)
        start_test.assert_called_once_with('login_check')


def test_start_all_schedulers_no_intervals_does_nothing():
    with mock.patch('ui_server.scheduler.add_test') as add_test, \
         mock.patch('ui_server.scheduler.start_test') as start_test:
        client = ui_server.app.test_client()
        response = client.post('/start_all_schedulers', data={})

        assert response.status_code == 302
        add_test.assert_not_called()
        start_test.assert_not_called()


def test_stop_scheduler_stops_jobs():
    with mock.patch('ui_server.scheduler.stop_all') as stop_all:
        client = ui_server.app.test_client()
        response = client.post('/stop_scheduler')

        assert response.status_code == 302
    stop_all.assert_called_once()


def test_run_login_once_triggers_check():
    with mock.patch('ui_server.trigger_login_check') as trig:
        client = ui_server.app.test_client()
        response = client.post('/run_login_once')

        assert response.status_code == 302
        trig.assert_called_once()


def test_results_endpoint_returns_latest_json():
    """GET /results should return the most recently posted results."""

    payload = {
        "results": {"svc": {"healthy": True, "message": "ok"}},
        "error": None,
    }
    fake_request._json = payload
    ui_server.receive_results()

    resp = ui_server.get_results()
    assert resp == payload


def test_index_reports_scheduler_not_running_when_no_process():
    captured = {}

    def fake_render_template(name, **kwargs):
        captured.update(kwargs)
        return ""

    with mock.patch('ui_server.render_template', side_effect=fake_render_template), \
         mock.patch('ui_server.scheduler.any_running', return_value=False):
        ui_server.index()

    assert captured.get('scheduler_running') is False


def test_index_reports_scheduler_running_when_process_active():
    captured = {}

    def fake_render_template(name, **kwargs):
        captured.update(kwargs)
        return ""

    with mock.patch('ui_server.render_template', side_effect=fake_render_template), \
         mock.patch('ui_server.scheduler.any_running', return_value=True):
        ui_server.index()

    assert captured.get('scheduler_running') is True


def test_index_uses_min_interval_for_polling():
    captured = {}

    def fake_render_template(name, **kwargs):
        captured.update(kwargs)
        return ""

    with mock.patch('ui_server.render_template', side_effect=fake_render_template), \
         mock.patch('ui_server.scheduler.any_running', return_value=True), \
         mock.patch('ui_server.scheduler.get_min_interval', return_value=7.0):
        ui_server.index()

    assert captured.get('poll_interval_ms') == 7000
