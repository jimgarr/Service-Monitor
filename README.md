# Health Monitoring Project

## Overview

This project provides a health monitoring API and UI. The API server runs health checks and sends results to a Teams webhook and to the UI server for display.

## Configuration

The current application only implementes a login service check but has the capability to add more.
When adding more services to be checked, required evironment variables should be included inside a `.env` file.
To see how the application functions for the login service, copy `.env.example` to `.env` and fill in the values for your environment.

### Environment Variables for Login Service Check

The application reads configuration from the `.env` file. See [`.env.example`](./.env.example) for reference. Required variables are:

- `UI_HOST` – host interface for the UI server.
- `UI_PORT` – port on which the UI server listens.
- `LOGIN_BASE_URL` – base URL of the monitored application.
- `LOGIN_USERNAME` – username for the login check.
- `LOGIN_PASSWORD` – password for the login check.
- `WEBHOOK_URL` – Teams webhook used for notifications.

## Adding Tests

Services are defined using the `Service` dataclass, which stores a `name`, a `check_health` callable, and an optional `display_name` used in the UI. Each check lives in the `health_checks` package; for example, the login check is implemented in `health_checks/login_check.py`.

To add a new test:

1. Create a module under `health_checks/` with a function that returns `HealthResult`.
2. Register the function by adding a `Service` to the `services` list in `api_server.py` for on-demand API checks or by calling `scheduler.add_test(name, fn, interval)` in `scheduler.py`.
3. To expose the check in the UI, update `templates/index.html` with a **Run Once** button and interval input for your service, and mirror those fields in `ui_server.py` so the form posts the interval to `scheduler.add_test`.
4. Add any required configuration to your `.env` file and restart the server or scheduler.

## Usage

### 1. Run the UI server

```sh
python ui_server.py
```

This command also launches the API server. Then open
http://`UI_Host`:`UI_PORT` in your browser.

### 2. Set the interval

Specify how often the login check should run (in seconds).

### 3. Start the scheduler

Click **Start Scheduler** to begin running the login check. Results will appear on the page automatically.
The page now refreshes the displayed results every few seconds while the scheduler is running.
### 4. Stop the scheduler


Use **Stop Scheduler** at any time to cancel all checks. The API server shuts down automatically when the UI server exits.

#### Notes

- The UI server only displays results sent to it; it does not run health checks itself.
- Teams notifications are only sent when checks are executed.

## Scheduler

`scheduler.py` can be used to run health checks on a fixed interval. Register
tests with `add_test(name, fn, interval)` and start them with `start_all()` or
`start_test(name)`. Results are pushed to the UI server for display.

The first check executes immediately after the scheduler starts. Subsequent
runs occur after each configured interval.

