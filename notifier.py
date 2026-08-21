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
    """Send a rich Discord webhook notification for an evaluated listing (deal_score >= 5)."""
    if not webhook_url:
        logger.info("Discord webhook URL not configured, skipping Discord notification.")
        return False

    # Color & icon formatting based on verdict and deal_score
    if evaluation.verdict == "OKAZJA" or evaluation.deal_score >= 8:
        color = 3066993  # Green
        status_icon = f"🚨 OKAZJA [{evaluation.deal_score}/10]"
    elif evaluation.verdict == "OBSERWUJ" or evaluation.deal_score >= 5:
        color = 16776960  # Yellow
        status_icon = f"👀 OBSERWUJ [{evaluation.deal_score}/10]"
    else:
        color = 10066329  # Grey
        status_icon = f"⚠️ ODRZUĆ [{evaluation.deal_score}/10]"

    embed = {
        "title": f"{status_icon} [{listing.category} - {listing.platform}] {evaluation.item_title}",
        "url": listing.url,
        "color": color,
        "fields": [
            {"name": "Werdykt i Ocena AI", "value": f"**{evaluation.verdict} [{evaluation.deal_score}/10]**", "inline": True},
            {"name": "Cena Vinted", "value": f"**{listing.price:.2f} {listing.currency}**", "inline": True},
            {"name": "Szacowana Cena Rynkowa", "value": f"**{evaluation.estimated_market_value} PLN**", "inline": True},
            {"name": "Szacowany Koszt Naprawy", "value": f"{evaluation.estimated_repair_cost} PLN", "inline": True},
            {"name": "Zysk na Czysto (Net Profit)", "value": f"**+{evaluation.net_profit_pln} PLN** (ROI: {evaluation.roi_percentage}%)", "inline": True},
            {"name": "Wykryta Usterka / Stan", "value": evaluation.detected_fault[:1024], "inline": False},
            {"name": "Uzasadnienie Qwen 2.5", "value": evaluation.reasoning[:1024], "inline": False},
            {"name": "Bezpośredni link do oferty", "value": f"[Kliknij, aby przejść do ogłoszenia]({listing.url})", "inline": False}
        ],
        "footer": {"text": f"Kategoria: {listing.category} | Platforma: {listing.platform} | ID: {listing.id}"}
    }

    if listing.image_url:
        embed["thumbnail"] = {"url": listing.image_url}

    payload = {
        "content": f"🎯 Wykryto ofertę ze statusem **{evaluation.verdict} [{evaluation.deal_score}/10]** w kategorii **{listing.category}**:",
        "embeds": [embed]
    }

    should_close = False
    if client is None:
        client = httpx.Client(timeout=10.0)
        should_close = True

    try:
        response = client.post(webhook_url, json=payload)
        response.raise_for_status()
        logger.info(f"Successfully sent Discord notification for {listing.id} ({evaluation.verdict} [{evaluation.deal_score}/10])")
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
    """Send a Telegram notification for an evaluated listing."""
    if not bot_token or not chat_id:
        logger.info("Telegram bot token or chat ID not configured, skipping Telegram notification.")
        return False

    status_icon = "🚨 OKAZJA" if evaluation.verdict == "OKAZJA" else "👀 OBSERWUJ"

    message_text = (
        f"<b>{status_icon} [{evaluation.deal_score}/10] - [{listing.category} - {listing.platform}]</b>\n\n"
        f"<b>Tytuł:</b> {evaluation.item_title}\n"
        f"<b>Cena Vinted:</b> {listing.price:.2f} {listing.currency}\n"
        f"<b>Wartość rynkowa:</b> {evaluation.estimated_market_value} PLN\n"
        f"<b>Koszt części/naprawy:</b> {evaluation.estimated_repair_cost} PLN\n"
        f"🔥 <b>ZYSK NA CZYSTO: {evaluation.net_profit_pln} PLN</b> (ROI: {evaluation.roi_percentage}%)\n"
        f"<b>Usterka / Stan:</b> {evaluation.detected_fault}\n\n"
        f"💡 <b>Uzasadnienie AI:</b> {evaluation.reasoning}\n\n"
        f"🔗 <a href='{listing.url}'>Zobacz ogłoszenie na {listing.platform}</a>"
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
    """Send notification to all enabled channels for deal_score >= 5."""
    results = {}
    results["discord"] = send_discord_notification(listing, evaluation, webhook_url=discord_webhook_url, client=client)
    results["telegram"] = send_telegram_notification(listing, evaluation, bot_token=telegram_bot_token, chat_id=telegram_chat_id, client=client)
    return results
