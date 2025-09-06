"""Health check for login/logout functionality."""

from monitorlib.monitor import HealthResult
import urllib.request
import json


def check_login(base_url: str, username: str, password: str) -> HealthResult:
    """Attempt to log in and then log out using the provided credentials."""
    login_url = base_url.rstrip('/') + '/enable-api/login'
    logout_url = base_url.rstrip('/') + '/enable-api/logout'

    try:
        login_req = urllib.request.Request(
            login_url,
            data=json.dumps({"login": username, "password": password}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(login_req, timeout=10) as resp:
            body = json.loads(resp.read().decode())
            cookie_headers = resp.headers.get_all("Set-Cookie") if hasattr(resp, "headers") else []
    except Exception as exc:
        return HealthResult(False, str(exc))

    if not body.get("success"):
        message = body.get("error", "Login failed")
        return HealthResult(False, f"Login failed: {message}")

    cookies = []
    if cookie_headers:
        from http.cookies import SimpleCookie

        simple_cookie = SimpleCookie()
        for header in cookie_headers:
            simple_cookie.load(header)
        epimresttoken = simple_cookie.get("epimresttoken")
        ewtoken = simple_cookie.get("ewtoken")
        if epimresttoken:
            cookies.append(f"epimresttoken={epimresttoken.value}")
        if ewtoken:
            cookies.append(f"ewtoken={ewtoken.value}")
    else:
        token = body.get("token", {}).get("token")
        if token:
            cookies.append(f"epimresttoken={token}")

    try:
        headers = {"Content-Type": "application/json"}
        if cookies:
            headers["Cookie"] = "; ".join(cookies)
        logout_req = urllib.request.Request(
            logout_url,
            data=json.dumps({"login": username}).encode("utf-8"),
            headers=headers,
        )
        with urllib.request.urlopen(logout_req) as resp:
            logout_body = json.loads(resp.read().decode())
            if not logout_body.get("success"):
                return HealthResult(False, "Logout failed or you are already logged out")
    except Exception as exc:
        return HealthResult(False, str(exc))

    return HealthResult(True, "Login/logout successful")
