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
    """Send a rich Discord webhook notification formatted for OKAZJA_FLIP or OKAZJA_NAPRAWA."""
    if not webhook_url:
        logger.info("Discord webhook URL not configured, skipping Discord notification.")
        return False

    color = 3066993  # Green color for qualified deals

    if evaluation.deal_type == "OKAZJA_FLIP":
        header_tag = "🎯 [CZYSTY FLIP]"
    elif evaluation.deal_type == "OKAZJA_NAPRAWA":
        header_tag = "🛠️ [DO NAPRAWY]"
    else:
        header_tag = "⚠️ [OKAZJA]"

    title_str = f"{header_tag} [{listing.category} - {listing.platform}] {evaluation.item_title}"

    if isinstance(evaluation.repair_steps, list):
        steps_formatted = " | ".join(evaluation.repair_steps) if evaluation.repair_steps else "Brak"
    else:
        steps_formatted = str(evaluation.repair_steps)

    fields = [
        {
            "name": "💰 **Finanse:**",
            "value": (
                f"Cena Vinted: **{listing.price:.2f} {listing.currency}** | "
                f"Rynkowa: **{evaluation.estimated_market_value} PLN** | "
                f"Szacowany zysk czysty: 🔥 **+{evaluation.estimated_net_profit} PLN** (ROI: {evaluation.roi_percentage}%)"
            ),
            "inline": False
        },
        {
            "name": "🎯 **Strategia:**",
            "value": (
                f"Sugerowana oferta: **{evaluation.negotiation_target} PLN** | "
                f"Płynność rynku: **{evaluation.market_liquidity}**"
            ),
            "inline": False
        }
    ]

    if evaluation.deal_type == "OKAZJA_NAPRAWA" or evaluation.estimated_parts_cost > 0:
        fields.append({
            "name": "🛠️ **Diagnoza i Plan:**",
            "value": (
                f"**Diagnoza:** {evaluation.fault_analysis}\n"
                f"**Trudność:** {evaluation.repair_difficulty} | "
                f"**Koszt części:** {evaluation.estimated_parts_cost} PLN\n"
                f"**Plan:** {steps_formatted}"
            ),
            "inline": False
        })

    fields.append({
        "name": "🛡️ **Ryzyko i Plan B:**",
        "value": (
            f"Poziom ryzyka: **{evaluation.risk_assessment}**\n"
            f"Wartość na części (Plan B): **{evaluation.salvage_value} PLN**\n"
            f"💡 *Uzasadnienie Qwen 2.5:* {evaluation.reasoning}"
        ),
        "inline": False
    })

    fields.append({
        "name": "🔗 **Link do oferty:**",
        "value": f"[Kliknij, aby otworzyć ogłoszenie na {listing.platform}]({listing.url})",
        "inline": False
    })

    embed = {
        "title": title_str,
        "url": listing.url,
        "color": color,
        "fields": fields,
        "footer": {"text": f"Kategoria: {listing.category} | Ocena AI: {evaluation.deal_score}/10 | ID: {listing.id}"}
    }

    if listing.image_url:
        embed["thumbnail"] = {"url": listing.image_url}

    payload = {
        "content": f"{header_tag} Wykryto nową ofertę w kategorii **{listing.category}**:",
        "embeds": [embed]
    }

    should_close = False
    if client is None:
        client = httpx.Client(timeout=10.0)
        should_close = True

    try:
        response = client.post(webhook_url, json=payload)
        response.raise_for_status()
        logger.info(f"Successfully sent Discord notification for {listing.id} ({evaluation.deal_type})")
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

    header_tag = "🎯 [CZYSTY FLIP]" if evaluation.deal_type == "OKAZJA_FLIP" else "🛠️ [DO NAPRAWY]"

    message_text = (
        f"<b>{header_tag} [{listing.category} - {listing.platform}]</b>\n\n"
        f"<b>Tytuł:</b> {evaluation.item_title}\n"
        f"💰 <b>Cena Vinted:</b> {listing.price:.2f} {listing.currency}\n"
        f"📈 <b>Rynkowa:</b> {evaluation.estimated_market_value} PLN\n"
        f"🔥 <b>ZYSK CZYSTY: +{evaluation.estimated_net_profit} PLN</b> (ROI: {evaluation.roi_percentage}%)\n\n"
        f"🎯 <b>Sugerowana oferta:</b> {evaluation.negotiation_target} PLN | <b>Płynność:</b> {evaluation.market_liquidity}\n"
        f"🛡️ <b>Ryzyko:</b> {evaluation.risk_assessment}\n"
        f"⚙️ <b>Wartość na części (Plan B):</b> {evaluation.salvage_value} PLN\n\n"
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
    """Send notification to all enabled channels."""
    results = {}
    results["discord"] = send_discord_notification(listing, evaluation, webhook_url=discord_webhook_url, client=client)
    results["telegram"] = send_telegram_notification(listing, evaluation, bot_token=telegram_bot_token, chat_id=telegram_chat_id, client=client)
    return results
