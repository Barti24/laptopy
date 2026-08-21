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
                "estimated_net_profit": 280,  # 500 - 200 - 20 = 280
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
        model_name="qwen2.5:14b",
        profit_threshold_flip=80.0
    )

    assert result.deal_type == "OKAZJA_FLIP"
    assert result.deal_score == 9
    assert result.estimated_market_value == 500
    assert result.estimated_parts_cost == 0
    assert result.estimated_net_profit == 280
    assert result.is_profitable is True
    assert result.negotiation_target == 170
    assert result.market_liquidity == "BARDZO SZYBKO"

def test_evaluate_listing_do_naprawy():
    mock_listing = Listing(
        id="test_repair_1",
        title="Ender 3 zatkana dysza",
        price=150.0,
        currency="PLN",
        description="Drukarka 3D zatkana dysza hotend.",
        url="https://example.com/ender3",
        platform="Vinted",
        category="Drukarki 3D"
    )

    ollama_response = {
        "message": {
            "content": json.dumps({
                "item_title": "Ender 3 Pro",
                "category": "Drukarki 3D",
                "deal_type": "OKAZJA_NAPRAWA",
                "deal_score": 8,
                "estimated_market_value": 450,
                "negotiation_target": 120,
                "market_liquidity": "ŚREDNIO",
                "risk_assessment": "NISKIE - drobna usterka eksploatacyjna",
                "salvage_value": 200,
                "fault_analysis": "Zatkana dysza ekstrudera",
                "repair_difficulty": "ŁATWA",
                "repair_steps": ["1. Wymiana dyszy hotend", "2. Poziomowanie stolu"],
                "estimated_parts_cost": 20,
                "estimated_net_profit": 260,  # 450 - (150 + 20 + 20) = 260
                "reasoning": "Tania naprawa hotendu daje duży zysk."
            })
        }
    }

    transport = httpx.MockTransport(lambda req: httpx.Response(200, json=ollama_response))
    client = httpx.Client(transport=transport)

    result = evaluate_listing_with_ollama(
        mock_listing,
        client=client,
        profit_threshold_repair=100.0
    )

    assert result.deal_type == "OKAZJA_NAPRAWA"
    assert result.deal_score == 8
    assert result.estimated_parts_cost == 20
    assert result.estimated_net_profit == 260
    assert result.is_profitable is True
    assert result.repair_difficulty == "ŁATWA"

def test_evaluate_listing_blacklisted_override_brak_zysku():
    mock_listing = Listing(
        id="test_macbook_2011",
        title="MacBook Pro 15 2011 uszkodzona grafika",
        price=200.0,
        currency="PLN",
        description="Gpu radeon zalany.",
        url="https://example.com/macbook2011",
        platform="Vinted",
        category="Laptopy"
    )

    ollama_response = {
        "message": {
            "content": json.dumps({
                "item_title": "MacBook Pro 15 2011",
                "category": "Laptopy",
                "deal_type": "OKAZJA_NAPRAWA",
                "deal_score": 8,
                "estimated_market_value": 700,
                "estimated_parts_cost": 50,
                "reasoning": "Niska cena zakupu."
            })
        }
    }

    transport = httpx.MockTransport(lambda req: httpx.Response(200, json=ollama_response))
    client = httpx.Client(transport=transport)

    result = evaluate_listing_with_ollama(mock_listing, client=client)

    # Blacklisted -> Overridden to BRAK_ZYSKU
    assert result.deal_type == "BRAK_ZYSKU"
    assert result.deal_score <= 2
    assert result.is_profitable is False
