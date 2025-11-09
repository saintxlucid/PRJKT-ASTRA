"""
Notification skill for CHAT OS.
Handles notify.push intent for sending notifications via various channels.
"""
from __future__ import annotations

import logging
from typing import Any

from chat_os.executor import ExecutionContext, register_intent
from chat_os.plan import PlanStep

logger = logging.getLogger(__name__)


@register_intent("notify.push")
def handle_notify_push(step: PlanStep, ctx: ExecutionContext) -> dict[str, Any]:
    """
    Send notification via specified channel.

    Supported channels:
    - console: Log to console (default, no risk)
    - system: System tray notification (requires OS permissions)
    - telegram: Send Telegram message (requires bot token)
    - slack: Send Slack message (requires webhook)
    - webhook: POST to custom webhook URL

    Args:
        step.args:
            - channel: Notification channel (e.g., "console", "system", "telegram://chat_id")
            - message: Message content
            - title: Optional title for system notifications
            - priority: Optional priority (low/normal/high/urgent)

    Returns:
        Dict with keys: ok, channel, delivered
    """
    channel = step.args.get("channel", "console")
    message = step.args.get("message", "")
    title = step.args.get("title", "ASTRA Notification")
    priority = step.args.get("priority", "normal")

    if not message:
        return {"ok": False, "error": "Missing required arg: message"}

    try:
        # Parse channel URI
        if "://" in channel:
            protocol, target = channel.split("://", 1)
        else:
            protocol = channel
            target = None

        # Route to appropriate notification handler
        if protocol == "console":
            return _notify_console(message, title, priority)
        elif protocol == "system":
            return _notify_system(message, title, priority)
        elif protocol == "telegram":
            return _notify_telegram(message, target, title)
        elif protocol == "slack":
            return _notify_slack(message, target, title)
        elif protocol == "webhook":
            return _notify_webhook(message, target, title, priority)
        else:
            return {
                "ok": False,
                "error": f"Unsupported channel protocol: {protocol}",
            }

    except Exception as e:
        logger.error(f"Notification failed: {e}", exc_info=True)
        return {"ok": False, "error": f"Notification failed: {e}"}


def _notify_console(message: str, title: str, priority: str) -> dict[str, Any]:
    """Log notification to console."""
    priority_prefix = {
        "low": "ℹ️",
        "normal": "📢",
        "high": "⚠️",
        "urgent": "🚨",
    }.get(priority, "📢")

    logger.info(f"{priority_prefix} {title}: {message}")

    return {
        "ok": True,
        "channel": "console",
        "delivered": True,
        "method": "console_log",
    }


def _notify_system(message: str, title: str, priority: str) -> dict[str, Any]:
    """
    Show system tray notification.
    Falls back to console if system notifications unavailable.
    """
    try:
        # Try to use platform-specific notification
        import platform

        system = platform.system()

        if system == "Windows":
            # Use win10toast if available
            try:
                from win10toast import ToastNotifier

                toast = ToastNotifier()
                duration = 10 if priority in ("high", "urgent") else 5
                toast.show_toast(title, message, duration=duration, threaded=True)

                return {
                    "ok": True,
                    "channel": "system",
                    "delivered": True,
                    "method": "win10toast",
                }
            except ImportError:
                pass

        # Fallback to console
        logger.warning("System notifications not available, using console fallback")
        return _notify_console(message, title, priority)

    except Exception as e:
        logger.error(f"System notification failed: {e}")
        return _notify_console(message, title, priority)


def _notify_telegram(message: str, chat_id: str | None, title: str) -> dict[str, Any]:
    """
    Send Telegram message.
    Requires TELEGRAM_BOT_TOKEN environment variable.
    """
    import os

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not bot_token:
        return {
            "ok": False,
            "error": "TELEGRAM_BOT_TOKEN environment variable not set",
            "channel": "telegram",
        }

    if not chat_id:
        return {
            "ok": False,
            "error": "Telegram chat_id required (use telegram://chat_id)",
            "channel": "telegram",
        }

    try:
        import requests

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": f"*{title}*\n\n{message}",
            "parse_mode": "Markdown",
        }

        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()

        return {
            "ok": True,
            "channel": f"telegram://{chat_id}",
            "delivered": True,
            "method": "telegram_bot_api",
        }

    except Exception as e:
        logger.error(f"Telegram notification failed: {e}")
        return {
            "ok": False,
            "error": f"Telegram send failed: {e}",
            "channel": "telegram",
        }


def _notify_slack(message: str, webhook_url: str | None, title: str) -> dict[str, Any]:
    """
    Send Slack message via webhook.
    """
    if not webhook_url:
        return {
            "ok": False,
            "error": "Slack webhook URL required (use slack://webhook_url)",
            "channel": "slack",
        }

    try:
        import requests

        payload = {
            "text": f"*{title}*",
            "blocks": [
                {"type": "header", "text": {"type": "plain_text", "text": title}},
                {"type": "section", "text": {"type": "mrkdwn", "text": message}},
            ],
        }

        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()

        return {
            "ok": True,
            "channel": "slack",
            "delivered": True,
            "method": "slack_webhook",
        }

    except Exception as e:
        logger.error(f"Slack notification failed: {e}")
        return {
            "ok": False,
            "error": f"Slack send failed: {e}",
            "channel": "slack",
        }


def _notify_webhook(
    message: str, url: str | None, title: str, priority: str
) -> dict[str, Any]:
    """
    POST notification to custom webhook.
    """
    if not url:
        return {
            "ok": False,
            "error": "Webhook URL required (use webhook://url)",
            "channel": "webhook",
        }

    try:
        import requests

        payload = {
            "title": title,
            "message": message,
            "priority": priority,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        }

        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()

        return {
            "ok": True,
            "channel": f"webhook://{url}",
            "delivered": True,
            "method": "http_post",
        }

    except Exception as e:
        logger.error(f"Webhook notification failed: {e}")
        return {
            "ok": False,
            "error": f"Webhook POST failed: {e}",
            "channel": "webhook",
        }
