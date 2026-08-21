import pytest
import json
import httpx
from models import Listing, EvaluationResult
from notifier import send_discord_notification, send_telegram_notification, notify_profitable_listing

def test_send_discord_notification_okazja_green():
    listing = Listing(
        id="vinted_100",
        title="Ender 3 Pro zatkana dysza",
        price=200.0,
        currency="PLN",
        description="Drukarka 3D z zatkanym ekstruderem.",
        url="https://vinted.pl/items/100",
        platform="Vinted",
        category="Drukarki 3D",
        image_url="https://images.vinted.net/100.jpg"
    )
    evaluation = EvaluationResult(
        item_title="Ender 3 Pro",
        category="Drukarki 3D",
        detected_fault="Zatkana dysza",
        difficulty_level="Prosta",
        deal_score=9,
        verdict="OKAZJA",
        estimated_market_value=500,
        estimated_repair_cost=20,
        net_profit_pln=250,
        roi_percentage=100,
        is_profitable=True,
        reasoning="Świetna marża przy prostej wymianie części."
    )

    captured_requests = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        data = json.loads(request.content.decode("utf-8"))
        assert "embeds" in data
        embed = data["embeds"][0]
        assert embed["color"] == 3066993  # Green
        assert "OKAZJA [9/10]" in embed["title"]
        return httpx.Response(204)

    client = httpx.Client(transport=httpx.MockTransport(mock_handler))
    success = send_discord_notification(listing, evaluation, webhook_url="https://discord.com/api/webhooks/test", client=client)
    assert success is True
    assert len(captured_requests) == 1

def test_send_discord_notification_obserwuj_yellow():
    listing = Listing(
        id="vinted_200",
        title="Amplituner Yamaha trzeszczy kanał",
        price=150.0,
        currency="PLN",
        description="Trzeszczy prawy kanał.",
        url="https://vinted.pl/items/200",
        platform="Vinted",
        category="Sprzęt Audio"
    )
    evaluation = EvaluationResult(
        item_title="Amplituner Yamaha",
        category="Sprzęt Audio",
        detected_fault="Trzeszczący potencjometr",
        difficulty_level="Średnia",
        deal_score=6,
        verdict="OBSERWUJ",
        estimated_market_value=300,
        estimated_repair_cost=30,
        net_profit_pln=90,
        roi_percentage=42,
        is_profitable=True,
        reasoning="Ciekawa oferta warta obserwacji."
    )

    def mock_handler(request: httpx.Request) -> httpx.Response:
        data = json.loads(request.content.decode("utf-8"))
        embed = data["embeds"][0]
        assert embed["color"] == 16776960  # Yellow for OBSERWUJ
        assert "OBSERWUJ [6/10]" in embed["title"]
        return httpx.Response(204)

    client = httpx.Client(transport=httpx.MockTransport(mock_handler))
    success = send_discord_notification(listing, evaluation, webhook_url="https://discord.com/api/webhooks/test", client=client)
    assert success is True

def test_send_telegram_notification_success():
    listing = Listing(
        id="vinted_300",
        title="Amplituner Pioneer",
        price=100.0,
        currency="PLN",
        description="Brak dźwięku.",
        url="https://vinted.pl/items/300",
        platform="Vinted",
        category="Sprzęt Audio"
    )
    evaluation = EvaluationResult(
        item_title="Amplituner Pioneer",
        category="Sprzęt Audio",
        detected_fault="Brak dźwięku na wyjściu",
        difficulty_level="Średnia",
        deal_score=8,
        verdict="OKAZJA",
        estimated_market_value=300,
        estimated_repair_cost=30,
        net_profit_pln=140,
        roi_percentage=87,
        is_profitable=True,
        reasoning="Opłacalna wymiana przekaźnika."
    )

    def mock_handler(request: httpx.Request) -> httpx.Response:
        data = json.loads(request.content.decode("utf-8"))
        assert data["chat_id"] == "123456"
        assert "Amplituner Pioneer" in data["text"]
        return httpx.Response(200, json={"ok": True})

    client = httpx.Client(transport=httpx.MockTransport(mock_handler))
    success = send_telegram_notification(
        listing, evaluation, bot_token="mock_token", chat_id="123456", client=client
    )
    assert success is True
