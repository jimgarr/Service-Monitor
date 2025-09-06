"""Core monitoring logic used by the API and CLI helpers."""

from dataclasses import dataclass
from typing import Callable, List, Dict, Any, Optional
import json
import urllib.request

@dataclass
class HealthResult:
    """Result object returned from a service health check."""

    healthy: bool
    message: str


@dataclass
class Service:
    """A service with a name and a callable health check."""

    name: str
    check_health: Callable[[], HealthResult]
    display_name: Optional[str] = None


def send_webhook_alert(
    webhook_url: str,
    statuses: Dict[str, Dict[str, Any]],
    ui_url: Optional[str] = None,
) -> None:
    """Send one Teams message with the results of multiple services."""

    body_blocks = []
    # Build one card section per service with its status and message
    for name, info in statuses.items():
        healthy = info["healthy"]
        message = info["message"]
        status_text = "UP" if healthy else "DOWN"
        body_blocks.extend(
            [
                {
                    "type": "TextBlock",
                    "size": "Medium",
                    "weight": "Bolder",
                    "text": name,
                },
                {"type": "TextBlock", "text": message},
                {"type": "TextBlock", "text": f"Status: {status_text}"},
            ]
        )

    if ui_url:
        body_blocks.append(
            {
                "type": "TextBlock",
                "text": f"[View details]({ui_url})",
            }
        )

    # Build a simple adaptive card payload for Teams
    card = {
        "contentType": "application/vnd.microsoft.card.adaptive",
        "content": {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.3",
            "body": body_blocks,
        },
    }

    # The Power Automate flow expects attachments under triggerBody().body
    payload = {"body": {"attachments": [card]}}

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as response:
        # Consume response to ensure request is sent
        response.read()

def check_services(
    services: List[Service],
    webhook_url: Optional[str] = None,
    ui_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Run health checks for a list of services and send a summary alert."""

    statuses: Dict[str, Any] = {}
    any_failed = False
    for service in services:
        try:
            # Execute the health check and capture the result
            result = service.check_health()
            healthy = result.healthy
            message = result.message
        except Exception as e:
            # If the check raises, treat it as unhealthy
            healthy = False
            message = str(e)
        statuses[service.name] = {"healthy": healthy, "message": message}
        if not healthy:
            any_failed = True

    if webhook_url and any_failed:
        send_webhook_alert(webhook_url, statuses, ui_url)

    return statuses
