"""Telegram notification helper for pipeline alerting.

Sends alerts (e.g. pipeline failures) to a Telegram chat via the Bot API.
Credentials are read from environment variables — never hardcoded:

    KIBOY_TG_BOT_TOKEN   Telegram bot token (from @BotFather)
    KIBOY_TG_CHAT_ID     Target chat/channel id

If either var is unset, ``send_telegram`` becomes a logged no-op so the
pipeline never crashes just because alerting is unconfigured (fail-soft on
the notification path, fail-loud on the actual work).
"""

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger("kiboy")

_API_BASE = "https://api.telegram.org"
_TIMEOUT_SECONDS = 15


def send_telegram(message: str, *, timeout: int = _TIMEOUT_SECONDS) -> bool:
    """Send a plain-text message to the configured Telegram chat.

    Args:
        message: Text to send (max ~4096 chars per Telegram limits).
        timeout: Network timeout in seconds (capped per global rules).

    Returns:
        ``True`` if Telegram accepted the message, ``False`` otherwise
        (missing config, network error, or non-OK API response). Never
        raises — alerting must not take down the caller.
    """
    bot_token = os.environ.get("KIBOY_TG_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("KIBOY_TG_CHAT_ID", "").strip()

    if not bot_token or not chat_id:
        logger.warning(
            "Telegram alert skipped: KIBOY_TG_BOT_TOKEN / KIBOY_TG_CHAT_ID not set"
        )
        return False

    url = f"{_API_BASE}/bot{bot_token}/sendMessage"
    payload = urllib.parse.urlencode(
        {"chat_id": chat_id, "text": message[:4096]}
    ).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=payload, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            if body.get("ok"):
                return True
            logger.error("Telegram API returned not-ok: %s", body.get("description"))
            return False
    except (urllib.error.URLError, OSError, ValueError) as exc:
        logger.error("Telegram alert failed: %s", exc)
        return False
