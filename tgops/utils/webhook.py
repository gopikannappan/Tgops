"""Webhook alert dispatcher for Telegram bot and Slack webhooks."""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


async def send_alert(webhook_url: str, webhook_type: str, message: str) -> None:
    """
    Send an alert to a Telegram bot webhook or Slack webhook.

    For webhook_type='telegram': POST {"text": message} to the webhook URL.
    For webhook_type='slack': POST {"text": message} to the Slack incoming webhook URL.
    If webhook_url is empty, silently returns.
    """
    if not webhook_url:
        return

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if webhook_type == "slack":
                payload = {"text": message}
                response = await client.post(webhook_url, json=payload)
            else:
                # Telegram bot webhook — expects {"text": message}
                # If the URL contains a chat_id query param, pass it; otherwise just POST text
                payload = {"text": message}
                response = await client.post(webhook_url, json=payload)

            response.raise_for_status()
            logger.debug("Alert sent via %s webhook.", webhook_type)
    except httpx.HTTPStatusError as exc:
        logger.warning("Webhook alert failed with HTTP %d: %s", exc.response.status_code, exc)
    except httpx.RequestError as exc:
        logger.warning("Webhook alert request failed: %s", exc)
    except Exception as exc:
        logger.warning("Unexpected error sending webhook alert: %s", exc)
