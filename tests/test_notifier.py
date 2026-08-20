import pytest
import json
import httpx
from models import Listing, EvaluationResult
from notifier import send_discord_notification, send_telegram_notification, notify_profitable_listing

def test_send_discord_notification_success():
    listing = Listing(
        id="olx_100",
        title="Asus ROG Strix i7 RTX 3060",
        price=2500.0,
        currency="PLN",
        description="Gwarancja, stan bdb.",
        url="https://olx.pl/d/100",
        platform="OLX",
        image_url="https://img.olx.pl/100.jpg"
    )
    evaluation = EvaluationResult(
        estimated_market_value=3000.0,
        estimated_profit=500.0,
        reasoning="Bardzo dobra okazja pod flipping RTX 3060.",
        is_profitable=True
    )

    captured_requests = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        data = json.loads(request.content.decode("utf-8"))
        assert "embeds" in data
        assert data["embeds"][0]["title"] == "🚨 OKAZJA! [OLX] Asus ROG Strix i7 RTX 3060"
        return httpx.Response(204)

    client = httpx.Client(transport=httpx.MockTransport(mock_handler))
    success = send_discord_notification(listing, evaluation, webhook_url="https://discord.com/api/webhooks/test", client=client)
    assert success is True
    assert len(captured_requests) == 1

def test_send_telegram_notification_success():
    listing = Listing(
        id="vinted_200",
        title="MacBook Pro 13 2020 i5 16GB",
        price=1800.0,
        currency="PLN",
        description="Zadbany, sprawny.",
        url="https://vinted.pl/items/200",
        platform="Vinted"
    )
    evaluation = EvaluationResult(
        estimated_market_value=2200.0,
        estimated_profit=400.0,
        reasoning="Szybka odsprzedaż w okolicach 2200 zł.",
        is_profitable=True
    )

    def mock_handler(request: httpx.Request) -> httpx.Response:
        data = json.loads(request.content.decode("utf-8"))
        assert data["chat_id"] == "123456"
        assert "MacBook Pro 13" in data["text"]
        return httpx.Response(200, json={"ok": True})

    client = httpx.Client(transport=httpx.MockTransport(mock_handler))
    success = send_telegram_notification(
        listing, evaluation, bot_token="mock_token", chat_id="123456", client=client
    )
    assert success is True

def test_notify_profitable_listing_no_credentials():
    listing = Listing(
        id="test_300",
        title="Test Laptop",
        price=500.0,
        currency="PLN",
        description="Test description",
        url="https://example.com",
        platform="OLX"
    )
    evaluation = EvaluationResult(
        estimated_market_value=800.0,
        estimated_profit=300.0,
        reasoning="Test reasoning",
        is_profitable=True
    )

    results = notify_profitable_listing(listing, evaluation, discord_webhook_url="", telegram_bot_token="", telegram_chat_id="")
    assert results["discord"] is False
    assert results["telegram"] is False
