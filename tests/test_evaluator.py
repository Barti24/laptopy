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

def test_passes_pre_filter_expensive_and_no_fault_keyword():
    listing = Listing(
        id="test_3",
        title="Laptop HP Pavilion idealny komputer",
        price=600.0,  # >= cheap_threshold 250 PLN, and no fault keyword
        currency="PLN",
        description="Idealny w 100% sprawny komputerek.",
        url="https://example.com/3",
        platform="Vinted",
        category="Laptopy"
    )
    assert passes_pre_filter(listing, max_price=1200.0, cheap_threshold=250.0) is False

def test_evaluate_listing_scoring_okazja():
    mock_listing = Listing(
        id="test_console_okazja",
        title="PS4 Slim 500GB głośno chodzi uszkodzony napęd",
        price=200.0,
        currency="PLN",
        description="Konsola działa, wada napędu.",
        url="https://example.com/ps4",
        platform="Vinted",
        category="Konsole"
    )

    ollama_response = {
        "message": {
            "content": json.dumps({
                "item_title": "PS4 Slim 500GB",
                "category": "Konsole",
                "detected_fault": "Uszkodzony napęd laser KES-496",
                "difficulty_level": "Prosta",
                "deal_score": 9,
                "verdict": "OKAZJA",
                "estimated_market_value": 550,
                "estimated_repair_cost": 40,
                "reasoning": "Niska cena zakupu i tania część dają świetną opłacalność."
            })
        }
    }

    transport = httpx.MockTransport(lambda req: httpx.Response(200, json=ollama_response))
    client = httpx.Client(transport=transport)

    result = evaluate_listing_with_ollama(
        mock_listing,
        client=client,
        ollama_url="http://mock-ollama:11434",
        model_name="qwen2.5:14b"
    )

    assert result.deal_score == 9
    assert result.verdict == "OKAZJA"
    assert result.is_profitable is True
    assert result.estimated_market_value == 550
    assert result.estimated_repair_cost == 40
    assert result.net_profit_pln == 280  # 550 - (200 + 30 + 40) = 280

def test_evaluate_listing_scoring_obserwuj():
    mock_listing = Listing(
        id="test_obserwuj",
        title="Karta graficzna GTX 1060 pęknięty wentylator",
        price=180.0,
        currency="PLN",
        description="Wykruszony łopatka wentylatora.",
        url="https://example.com/gtx1060",
        platform="Vinted",
        category="Karty graficzne"
    )

    ollama_response = {
        "message": {
            "content": json.dumps({
                "item_title": "GTX 1060 6GB",
                "category": "Karty graficzne",
                "detected_fault": "Pęknięte chłodzenie / wentylator",
                "difficulty_level": "Prosta",
                "deal_score": 6,
                "verdict": "OBSERWUJ",
                "estimated_market_value": 350,
                "estimated_repair_cost": 30,
                "reasoning": "Umiarkowana marża, warta rozważenia po małej negocjacji."
            })
        }
    }

    transport = httpx.MockTransport(lambda req: httpx.Response(200, json=ollama_response))
    client = httpx.Client(transport=transport)

    result = evaluate_listing_with_ollama(mock_listing, client=client)

    assert result.deal_score == 6
    assert result.verdict == "OBSERWUJ"
    assert result.is_profitable is True

def test_evaluate_listing_blacklisted_override_odrzuc():
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
                "detected_fault": "Uszkodzone GPU Radeon",
                "difficulty_level": "Trudna",
                "deal_score": 8,
                "verdict": "OKAZJA",
                "estimated_market_value": 700,
                "estimated_repair_cost": 50,
                "reasoning": "Niska cena zakupu."
            })
        }
    }

    transport = httpx.MockTransport(lambda req: httpx.Response(200, json=ollama_response))
    client = httpx.Client(transport=transport)

    result = evaluate_listing_with_ollama(mock_listing, client=client)

    # Blacklisted -> Overridden to ODRZUĆ
    assert result.verdict == "ODRZUĆ"
    assert result.deal_score <= 3
    assert result.is_profitable is False
