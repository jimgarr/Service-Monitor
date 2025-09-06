# Health Monitoring Project

## Overview

This project provides a health monitoring API and UI. The API server runs health checks and sends results to a Teams webhook and to the UI server for display.

## Configuration

Copy `.env.example` to `.env` and fill in the values for your environment.


### Environment Variables

The application reads configuration from the `.env` file. See [`.env.example`](./.env.example) for reference. Required variables are:

- `UI_HOST` – host interface for the UI server.
- `UI_PORT` – port on which the UI server listens.
- `LOGIN_BASE_URL` – base URL of the monitored application.
- `LOGIN_USERNAME` – username for the login check.
- `LOGIN_PASSWORD` – password for the login check.
- `WEBHOOK_URL` – Teams webhook used for notifications.

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

