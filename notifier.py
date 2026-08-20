import logging
from typing import Optional, Dict
import httpx
from models import Listing, EvaluationResult
from config import DISCORD_WEBHOOK_URL, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)

def send_discord_notification(
    listing: Listing,
    evaluation: EvaluationResult,
    webhook_url: str = DISCORD_WEBHOOK_URL,
    client: Optional[httpx.Client] = None
) -> bool:
    """Send a rich Discord webhook notification for a profitable listing."""
    if not webhook_url:
        logger.info("Discord webhook URL not configured, skipping Discord notification.")
        return False

    embed = {
        "title": f"🚨 OKAZJA! [{listing.platform}] {listing.title}",
        "url": listing.url,
        "color": 3066993,  # Green color
        "fields": [
            {"name": "Cena w ogłoszeniu", "value": f"**{listing.price:.2f} {listing.currency}**", "inline": True},
            {"name": "Szacowana wartość", "value": f"**{evaluation.estimated_market_value:.2f} PLN**", "inline": True},
            {"name": "Szacowany ZYSK", "value": f"🔥 **+{evaluation.estimated_profit:.2f} PLN**", "inline": True},
            {"name": "Uzasadnienie AI (qwen2.5:14b)", "value": evaluation.reasoning[:1024], "inline": False},
        ],
        "footer": {"text": f"Platforma: {listing.platform} | ID: {listing.id}"}
    }

    if listing.image_url:
        embed["thumbnail"] = {"url": listing.image_url}

    payload = {
        "content": "🎯 Wykryto nową okazję do flippingu laptopa!",
        "embeds": [embed]
    }

    should_close = False
    if client is None:
        client = httpx.Client(timeout=10.0)
        should_close = True

    try:
        response = client.post(webhook_url, json=payload)
        response.raise_for_status()
        logger.info(f"Successfully sent Discord notification for {listing.id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send Discord notification for {listing.id}: {e}")
        return False
    finally:
        if should_close:
            client.close()

def send_telegram_notification(
    listing: Listing,
    evaluation: EvaluationResult,
    bot_token: str = TELEGRAM_BOT_TOKEN,
    chat_id: str = TELEGRAM_CHAT_ID,
    client: Optional[httpx.Client] = None
) -> bool:
    """Send a Telegram notification for a profitable listing."""
    if not bot_token or not chat_id:
        logger.info("Telegram bot token or chat ID not configured, skipping Telegram notification.")
        return False

    message_text = (
        f"🚨 <b>OKAZJA FLIPPING! [{listing.platform}]</b>\n\n"
        f"<b>Tytuł:</b> {listing.title}\n"
        f"<b>Cena:</b> {listing.price:.2f} {listing.currency}\n"
        f"<b>Szacowana wartość:</b> {evaluation.estimated_market_value:.2f} PLN\n"
        f"🔥 <b>ZYSK: +{evaluation.estimated_profit:.2f} PLN</b>\n\n"
        f"<b>Uzasadnienie AI:</b> {evaluation.reasoning}\n\n"
        f"🔗 <a href='{listing.url}'>Zobacz ogłoszenie</a>"
    )

    telegram_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message_text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }

    should_close = False
    if client is None:
        client = httpx.Client(timeout=10.0)
        should_close = True

    try:
        response = client.post(telegram_url, json=payload)
        response.raise_for_status()
        logger.info(f"Successfully sent Telegram notification for {listing.id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send Telegram notification for {listing.id}: {e}")
        return False
    finally:
        if should_close:
            client.close()

def notify_profitable_listing(
    listing: Listing,
    evaluation: EvaluationResult,
    discord_webhook_url: str = DISCORD_WEBHOOK_URL,
    telegram_bot_token: str = TELEGRAM_BOT_TOKEN,
    telegram_chat_id: str = TELEGRAM_CHAT_ID,
    client: Optional[httpx.Client] = None
) -> Dict[str, bool]:
    """Send notification to all enabled channels."""
    results = {}
    results["discord"] = send_discord_notification(listing, evaluation, webhook_url=discord_webhook_url, client=client)
    results["telegram"] = send_telegram_notification(listing, evaluation, bot_token=telegram_bot_token, chat_id=telegram_chat_id, client=client)
    return results
