import pytest
import json
import httpx
from models import Listing, EvaluationResult
from notifier import send_discord_notification, send_telegram_notification, notify_profitable_listing

def test_send_discord_notification_profitable_green():
    listing = Listing(
        id="olx_100",
        title="Ender 3 Pro zatkana dysza",
        price=200.0,
        currency="PLN",
        description="Drukarka 3D włącza się, dysza zatkana.",
        url="https://olx.pl/d/100",
        platform="OLX",
        category="Drukarki 3D",
        image_url="https://img.olx.pl/100.jpg"
    )
    evaluation = EvaluationResult(
        item_title="Ender 3 Pro",
        category="Drukarki 3D",
        detected_fault="Zatkana dysza hotend",
        difficulty_level="Prosta",
        estimated_parts_cost_pln=20,
        estimated_market_value_working_pln=450,
        net_profit_pln=215,
        roi_percentage=91,
        is_profitable=True,
        recommendation_reason="Prosta wymiana hotendu daje wysoki zysk netto."
    )

    captured_requests = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        data = json.loads(request.content.decode("utf-8"))
        assert "embeds" in data
        embed = data["embeds"][0]
        assert embed["color"] == 3066993  # Green
        assert "Ender 3 Pro" in embed["title"]
        assert "Zatkana dysza hotend" in embed["fields"][0]["value"]
        assert embed["fields"][5]["value"] == "**215 PLN**"
        return httpx.Response(204)

    client = httpx.Client(transport=httpx.MockTransport(mock_handler))
    success = send_discord_notification(listing, evaluation, webhook_url="https://discord.com/api/webhooks/test", client=client)
    assert success is True
    assert len(captured_requests) == 1

def test_send_discord_notification_risky_yellow():
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
        detected_fault="Uszkodzony potencjometr lub kondensatory",
        difficulty_level="Średnia",
        estimated_parts_cost_pln=40,
        estimated_market_value_working_pln=280,
        net_profit_pln=75,
        roi_percentage=36,
        is_profitable=False,  # Profit < 100 PLN
        recommendation_reason="Niska marża, ryzyko większej usterki w torze audio."
    )

    def mock_handler(request: httpx.Request) -> httpx.Response:
        data = json.loads(request.content.decode("utf-8"))
        embed = data["embeds"][0]
        assert embed["color"] == 16776960  # Yellow for non-profitable / risky
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
        estimated_parts_cost_pln=30,
        estimated_market_value_working_pln=300,
        net_profit_pln=155,
        roi_percentage=106,
        is_profitable=True,
        recommendation_reason="Opłacalna wymiana przekaźnika głośnikowego."
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
