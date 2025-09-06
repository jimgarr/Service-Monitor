"""Very small Flask API that exposes the monitoring functionality."""

import os
from typing import Any
import json
import subprocess
import requests
import time
from dotenv import load_dotenv

from flask import Flask, request, jsonify

from monitorlib.monitor import Service, check_services
from health_checks.login_check import check_login

app = Flask(__name__)
load_dotenv()

UI_HOST = os.environ["UI_HOST"]
UI_PORT = int(os.environ["UI_PORT"])
UI_URL = f"http://{UI_HOST}:{UI_PORT}"

LOGIN_BASE_URL = os.environ["LOGIN_BASE_URL"]
LOGIN_USERNAME = os.environ["LOGIN_USERNAME"]
LOGIN_PASSWORD = os.environ["LOGIN_PASSWORD"]

def ensure_ui_server():
    """Ensure the UI server is running, start if not."""
    try:
        requests.get(f"{UI_URL}/", timeout=1)
    except Exception:
        # Start UI server as subprocess
        subprocess.Popen(
            ["python", "ui_server.py"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        # Wait for UI server to start
        for _ in range(10):
            try:
                requests.get(f"{UI_URL}/", timeout=1)
                break
            except Exception:
                time.sleep(0.5)


@app.route("/check", methods=["POST"])
def check() -> Any:
    """Run the hard coded login check."""

    data = request.get_json(force=True) or {}
    webhook_url = data.get("webhook_url")

    services = [
        Service(
            "Login Check",
            lambda: check_login(
                LOGIN_BASE_URL,
                LOGIN_USERNAME,
                LOGIN_PASSWORD,
            ),
        )
    ]

    # Run the checks
    try:
        statuses = check_services(services, webhook_url, UI_URL if webhook_url else None)
        error = None
    except Exception as exc:
        statuses = None
        error = str(exc)

    # Ensure UI server is running and post results
    ensure_ui_server()
    try:
        requests.post(
            f"{UI_URL}/results",
            json={"results": statuses, "error": error},
            timeout=2,
        )
    except Exception as exc:
        # UI server failed to accept results
        pass


    return jsonify(statuses if statuses else {"error": error})

def main() -> None:
    """Entry point for running the API with ``python api_server.py``."""

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))


if __name__ == "__main__":
    main()
