import pytest
import json
import httpx
from models import Listing, EvaluationResult
from notifier import send_discord_notification, send_telegram_notification, notify_profitable_listing

def test_send_discord_notification_czysty_flip():
    listing = Listing(
        id="vinted_100",
        title="Ender 3 Pro jak nowa",
        price=200.0,
        currency="PLN",
        description="Drukarka 3D w 100% sprawna.",
        url="https://vinted.pl/items/100",
        platform="Vinted",
        category="Drukarki 3D",
        image_url="https://images.vinted.net/100.jpg"
    )
    evaluation = EvaluationResult(
        item_title="Ender 3 Pro",
        category="Drukarki 3D",
        deal_type="OKAZJA_FLIP",
        deal_score=9,
        estimated_market_value=500,
        estimated_parts_cost=0,
        estimated_net_profit=280,
        roi_percentage=140,
        negotiation_target=170,
        market_liquidity="BARDZO SZYBKO",
        risk_assessment="NISKIE - pewny flip",
        salvage_value=250,
        fault_analysis="Brak usterki / Sprzęt sprawny",
        repair_difficulty="Brak",
        repair_steps=["1. Wystawienie oferty"],
        is_profitable=True,
        reasoning="Świetna marża przy czystym flipie."
    )

    captured_requests = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        data = json.loads(request.content.decode("utf-8"))
        assert "embeds" in data
        embed = data["embeds"][0]
        assert embed["color"] == 3066993  # Green
        assert "🎯 [CZYSTY FLIP]" in embed["title"]
        assert "Sugerowana oferta: **170 PLN**" in embed["fields"][1]["value"]
        return httpx.Response(204)

    client = httpx.Client(transport=httpx.MockTransport(mock_handler))
    success = send_discord_notification(listing, evaluation, webhook_url="https://discord.com/api/webhooks/test", client=client)
    assert success is True
    assert len(captured_requests) == 1

def test_send_discord_notification_do_naprawy():
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
        deal_type="OKAZJA_NAPRAWA",
        deal_score=8,
        estimated_market_value=350,
        estimated_parts_cost=30,
        estimated_net_profit=150,
        roi_percentage=75,
        negotiation_target=120,
        market_liquidity="ŚREDNIO",
        risk_assessment="NISKIE - drobna wada potencjometru",
        salvage_value=150,
        fault_analysis="Trzeszczący potencjometr głosu",
        repair_difficulty="ŁATWA",
        repair_steps=["1. Czyszczenie Kontaktem", "2. Test odsłuchowy"],
        is_profitable=True,
        reasoning="Łatwa naprawa daje 150 PLN czystego zysku."
    )

    def mock_handler(request: httpx.Request) -> httpx.Response:
        data = json.loads(request.content.decode("utf-8"))
        embed = data["embeds"][0]
        assert embed["color"] == 3066993  # Green
        assert "🛠️ [DO NAPRAWY]" in embed["title"]
        assert "Trzeszczący potencjometr głosu" in embed["fields"][2]["value"]
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
        deal_type="OKAZJA_NAPRAWA",
        deal_score=8,
        estimated_market_value=300,
        estimated_parts_cost=30,
        estimated_net_profit=150,
        roi_percentage=100,
        negotiation_target=80,
        market_liquidity="ŚREDNIO",
        risk_assessment="NISKIE - przekaźnik",
        salvage_value=120,
        fault_analysis="Brak dźwięku na wyjściu",
        repair_difficulty="ŚREDNIA",
        repair_steps=["1. Wymiana przekaźnika głośnikowego"],
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
