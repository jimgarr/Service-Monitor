from unittest import mock
import os
import sys

# Ensure the package can be imported when running tests directly on Windows
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
import json

from monitorlib.monitor import HealthResult
from health_checks.login_check import check_login


def _make_resp(body, status=200, headers=None):
    class Headers(dict):
        def get_all(self, name):
            val = self.get(name)
            if val is None:
                return []
            if isinstance(val, list):
                return val
            return [val]

    class Resp:
        def __init__(self, body, status, headers):
            self.body = json.dumps(body).encode()
            self.status = status
            self.headers = Headers(headers or {})

        def read(self):
            return self.body

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            pass

    return Resp(body, status, headers)


def test_check_login_success():
    login_body = {
        "message": "enjoy your token",
        "success": True,
    }
    login_headers = {
        "Set-Cookie": [
            "epimresttoken=TOKEN; Path=/",
            "ewtoken=EWTOKEN; Path=/",
        ]
    }
    logout_body = {"message": "You are logged out", "success": True}
    responses = [
        _make_resp(login_body, headers=login_headers),
        _make_resp(logout_body),
    ]
    calls = []

    def side_effect(req, *args, **kwargs):
        calls.append(req)
        return responses[len(calls) - 1]

    with mock.patch("urllib.request.urlopen", side_effect=side_effect) as urlopen:
        result = check_login("https://example.com", "user", "pass")
        assert result == HealthResult(True, "Login/logout successful")
        assert urlopen.call_count == 2
        login_req = calls[0]
        logout_req = calls[1]
        assert login_req.full_url == "https://example.com/enable-api/login"
        assert json.loads(login_req.data.decode()) == {
            "login": "user",
            "password": "pass",
        }
        assert logout_req.full_url == "https://example.com/enable-api/logout"
        assert json.loads(logout_req.data.decode()) == {"login": "user"}
        assert (
            logout_req.headers["Cookie"]
            == "epimresttoken=TOKEN; ewtoken=EWTOKEN"
        )


def test_check_login_logout_success_false():
    login_body = {
        "message": "enjoy your token",
        "success": True,
    }
    login_headers = {
        "Set-Cookie": [
            "epimresttoken=TOKEN; Path=/",
            "ewtoken=EWTOKEN; Path=/",
        ]
    }
    logout_body = {"message": "already logged out?", "success": False}
    responses = [
        _make_resp(login_body, headers=login_headers),
        _make_resp(logout_body),
    ]
    calls = []

    def side_effect(req, *args, **kwargs):
        calls.append(req)
        return responses[len(calls) - 1]

    with mock.patch("urllib.request.urlopen", side_effect=side_effect) as urlopen:
        result = check_login("https://example.com", "user", "pass")
        assert result == HealthResult(
            False, "Logout failed or you are already logged out"
        )
        assert urlopen.call_count == 2
        logout_req = calls[1]
        assert (
            logout_req.headers["Cookie"]
            == "epimresttoken=TOKEN; ewtoken=EWTOKEN"
        )


def test_check_login_login_failure():
    login_body = {"error": "unauthorized please see enable-api logs", "success": False}
    responses = [_make_resp(login_body)]

    def side_effect(req, *args, **kwargs):
        return responses[0]

    with mock.patch("urllib.request.urlopen", side_effect=side_effect) as urlopen:
        result = check_login("https://example.com", "user", "pass")
        assert result == HealthResult(False, "Login failed: unauthorized please see enable-api logs")
        assert urlopen.call_count == 1


def test_check_login_logout_failure():
    login_body = {
        "message": "enjoy your token",
        "success": True,
    }
    login_headers = {
        "Set-Cookie": [
            "epimresttoken=TOKEN; Path=/",
            "ewtoken=EWTOKEN; Path=/",
        ]
    }
    responses = [_make_resp(login_body, headers=login_headers), RuntimeError("boom")]
    calls = []

    def side_effect(req, *args, **kwargs):
        if len(calls) == 0:
            calls.append(req)
            return responses[0]
        else:
            calls.append(req)
            raise responses[1]

    with mock.patch("urllib.request.urlopen", side_effect=side_effect) as urlopen:
        result = check_login("https://example.com", "user", "pass")
        assert result.healthy is False
        assert "boom" in result.message
        assert urlopen.call_count == 2
        logout_req = calls[1]
        assert (
            logout_req.headers["Cookie"]
            == "epimresttoken=TOKEN; ewtoken=EWTOKEN"
        )


def test_check_login_exception():
    def fail(req, *args, **kwargs):
        raise RuntimeError('boom')
    with mock.patch('urllib.request.urlopen', side_effect=fail) as urlopen:
        result = check_login('https://example.com', 'user', 'pass')
        assert result.healthy is False
        assert 'boom' in result.message
        assert urlopen.call_count == 1
