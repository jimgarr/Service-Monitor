"""Basic Flask web UI that displays health check results."""

import os
import subprocess
import sys
import atexit
import threading
import time
from flask import Flask, render_template, request, redirect, url_for

import requests
import scheduler


def _get_webhook_payload() -> dict:
    """Return payload with the Teams webhook URL from the environment."""
    return {"webhook_url": os.environ.get("WEBHOOK_URL", "")}

def trigger_login_check():
    payload = _get_webhook_payload()
    try:
        requests.post("http://localhost:8000/check", json=payload, timeout=5)
    except Exception:
        pass




app = Flask(__name__)

# Store the latest results in memory (for demo purposes). ``results`` is a
# mapping of service name to its most recent health information. Using a dict
# allows each service to update its own entry without overwriting others when
# the UI receives results for a single service.
latest_results = {"results": {}, "error": None}

# Number of distinct service results expected from the initial check run. When
# the UI first starts, it triggers a login check. Once this many individual
# results have been received, the initial run is considered complete.
INITIAL_RESULTS_EXPECTED = 1

# Track API server subprocess
api_process = None


def start_api_server() -> None:
    """Start the API server if it is not already running."""
    global api_process
    if api_process is None or api_process.poll() is not None:
        api_process = subprocess.Popen(
            [sys.executable, "api_server.py"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )


def stop_api_server() -> None:
    """Terminate the API server subprocess if running."""
    global api_process
    if api_process and api_process.poll() is None:
        api_process.terminate()
        try:
            api_process.wait(timeout=5)
        except Exception:
            pass
    api_process = None

@app.route("/", methods=["GET"])
def index():
    """Display the latest health check results."""
    scheduler_running = scheduler.any_running()
    poll_interval = scheduler.get_min_interval() or 5.0
    return render_template(
        "index.html",
        results=latest_results["results"],
        error=latest_results["error"],
        scheduler_running=scheduler_running,
        expected_initial=INITIAL_RESULTS_EXPECTED,
        poll_interval_ms=int(poll_interval * 1000),
    )

@app.route("/results", methods=["POST"])
def receive_results():
    """Receive health check results as JSON and store them."""
    data = request.get_json(force=True)

    # Merge new results with any previously stored ones so that different
    # services update their own entries without clobbering others.
    new_results = data.get("results") or {}
    if latest_results["results"] is None:
        latest_results["results"] = {}
    latest_results["results"].update(new_results)
    latest_results["error"] = data.get("error")
    return {"status": "ok"}


@app.route("/results", methods=["GET"])
def get_results():
    """Return the latest stored results as JSON."""
    return latest_results


@app.route("/start_all_schedulers", methods=["POST"])
def start_all_schedulers():
    """Start scheduled checks for available services."""

    login_raw = request.form.get("interval_login")

    if login_raw:
        try:
            interval_login = float(login_raw)
        except ValueError:
            interval_login = 60.0
        scheduler.add_test("login_check", trigger_login_check, interval_login)
        scheduler.start_test("login_check")

    return redirect(url_for("index"))


@app.route("/stop_scheduler", methods=["POST"])
def stop_scheduler():
    """Stop all scheduled jobs."""

    scheduler.stop_all()

    return redirect(url_for("index"))


@app.route("/run_login_once", methods=["POST"])
def run_login_once():
    """Run the login check a single time."""
    trigger_login_check()
    return redirect(url_for("index"))


def _run_initial_checks() -> None:
    """Trigger all health checks once after the servers start."""
    # Give the UI server a moment to start accepting requests
    time.sleep(1)
    trigger_login_check()

def main() -> None:
    """Run the UI server when executed as a script."""
    start_api_server()
    atexit.register(stop_api_server)
    # Launch initial checks in a background thread so results appear shortly
    # after startup without blocking the server from running.
    threading.Thread(target=_run_initial_checks, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("UI_PORT", 5000)))

if __name__ == "__main__":
    main()
