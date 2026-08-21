import pytest
import json
import httpx
from models import Listing
from ollama_evaluator import evaluate_listing_with_ollama
from main import passes_pre_filter

def test_passes_pre_filter_keyword_matching():
    listing = Listing(
        id="test_1",
        title="Laptop Lenovo ThinkPad T14 do naprawy uszkodzony ekran",
        price=500.0,
        currency="PLN",
        description="Laptop nie działa, zbity ekran.",
        url="https://example.com/1",
        platform="Vinted",
        category="Laptopy"
    )
    assert passes_pre_filter(listing, max_price=1200.0, cheap_threshold=250.0) is True

def test_passes_pre_filter_exclude_parts_laptop():
    listing = Listing(
        id="test_exclude_parts",
        title="RAM DDR4 8GB do laptopa Lenovo uszkodzony",
        price=50.0,
        currency="PLN",
        description="Pamięć ram do komputera.",
        url="https://example.com/ram",
        platform="Vinted",
        category="Laptopy"
    )
    # Excluded because title contains 'ram' in Laptopy category
    assert passes_pre_filter(listing, max_price=1200.0, cheap_threshold=250.0) is False

def test_passes_pre_filter_cheap_auto_pass():
    listing = Listing(
        id="test_cheap_pass",
        title="Laptop Dell ładny komputer",
        price=200.0,  # Below cheap_threshold 250 PLN
        currency="PLN",
        description="Ładny notebook z zasilaczem.",
        url="https://example.com/cheap",
        platform="Vinted",
        category="Laptopy"
    )
    assert passes_pre_filter(listing, max_price=1200.0, cheap_threshold=250.0) is True

def test_passes_pre_filter_exceeds_max_price():
    listing = Listing(
        id="test_2",
        title="Laptop Asus ROG uszkodzony dysk",
        price=1500.0,  # Exceeds max_price 1200 PLN
        currency="PLN",
        description="Uszkodzony dysk.",
        url="https://example.com/2",
        platform="Vinted",
        category="Laptopy"
    )
    assert passes_pre_filter(listing, max_price=1200.0, cheap_threshold=250.0) is False

def test_evaluate_listing_timeout_handling():
    mock_listing = Listing(
        id="test_timeout_1",
        title="Laptop Lenovo ThinkPad T14",
        price=300.0,
        currency="PLN",
        description="Nietestowany laptop.",
        url="https://example.com/timeout",
        platform="Vinted",
        category="Laptopy"
    )

    def mock_timeout_handler(request: httpx.Request) -> httpx.Response:
        req_body = json.loads(request.content.decode("utf-8"))
        assert "options" in req_body
        assert req_body["options"]["num_predict"] == 300
        assert req_body["options"]["temperature"] == 0.1
        raise httpx.TimeoutException("Read timeout after 600s")

    transport = httpx.MockTransport(mock_timeout_handler)
    client = httpx.Client(transport=transport)

    result = evaluate_listing_with_ollama(mock_listing, client=client)

    assert result.deal_type == "BRAK_ZYSKU"
    assert result.is_profitable is False
    assert "Przekroczono limit czasu" in result.reasoning

def test_evaluate_listing_czysty_flip():
    mock_listing = Listing(
        id="test_flip_1",
        title="PS4 Slim 500GB jak nowa komplet gier",
        price=200.0,
        currency="PLN",
        description="Konsola w 100% sprawna z okablowaniem.",
        url="https://example.com/ps4flip",
        platform="Vinted",
        category="Konsole"
    )

    ollama_response = {
        "message": {
            "content": json.dumps({
                "item_title": "PS4 Slim 500GB",
                "category": "Konsole",
                "deal_type": "OKAZJA_FLIP",
                "deal_score": 9,
                "estimated_market_value": 500,
                "negotiation_target": 170,
                "market_liquidity": "BARDZO SZYBKO",
                "risk_assessment": "NISKIE - sprawny sprzęt z pewną marżą",
                "salvage_value": 250,
                "fault_analysis": "Brak usterki / Sprzęt sprawny",
                "repair_difficulty": "Brak",
                "repair_steps": ["1. Czyszczenie", "2. Wystawienie oferty"],
                "estimated_parts_cost": 0,
                "estimated_net_profit": 280,
                "reasoning": "Bardzo niska cena za w 100% sprawną konsolę."
            })
        }
    }

    transport = httpx.MockTransport(lambda req: httpx.Response(200, json=ollama_response))
    client = httpx.Client(transport=transport)

    result = evaluate_listing_with_ollama(
        mock_listing,
        client=client,
        ollama_url="http://mock-ollama:11434",
        model_name="qwen2.5:7b",
        profit_threshold_flip=80.0
    )

    assert result.deal_type == "OKAZJA_FLIP"
    assert result.deal_score == 9
    assert result.estimated_market_value == 500
    assert result.estimated_parts_cost == 0
    assert result.estimated_net_profit == 280
    assert result.is_profitable is True
