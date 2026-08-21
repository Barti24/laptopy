import pytest
import json
import httpx
from models import Listing
from ollama_evaluator import evaluate_listing_with_ollama
from main import passes_pre_filter

def test_passes_pre_filter_valid():
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
    assert passes_pre_filter(listing, max_price=800.0) is True

def test_passes_pre_filter_exceeds_max_price():
    listing = Listing(
        id="test_2",
        title="Laptop Asus ROG uszkodzony dysk",
        price=1200.0,
        currency="PLN",
        description="Uszkodzony dysk.",
        url="https://example.com/2",
        platform="Vinted",
        category="Laptopy"
    )
    assert passes_pre_filter(listing, max_price=800.0) is False

def test_passes_pre_filter_no_fault_keyword():
    listing = Listing(
        id="test_3",
        title="Laptop HP Pavilion w idealnym stanie jak nowy",
        price=400.0,
        currency="PLN",
        description="Super stan, pełen komplet gier i akcesoriów.",
        url="https://example.com/3",
        platform="Vinted",
        category="Laptopy"
    )
    assert passes_pre_filter(listing, max_price=800.0) is False

def test_evaluate_listing_repair_profitable_dynamic_resale():
    mock_listing = Listing(
        id="test_console_1",
        title="PS4 Slim 500GB nie czyta płyt głośno chodzi",
        price=250.0,
        currency="PLN",
        description="Konsola włącza się, ale napęd nie pobiera płyt. Wymaga czyszczenia.",
        url="https://example.com/ps4",
        platform="Vinted",
        category="Konsole"
    )

    ollama_response = {
        "message": {
            "content": json.dumps({
                "item_title": "PS4 Slim 500GB",
                "category": "Konsole",
                "detected_fault": "Uszkodzony laser/napęd KES-496 oraz zapchane chłodzenie",
                "difficulty_level": "Prosta",
                "estimated_parts_cost_pln": 50,
                "estimated_resale_price_pln": 500,
                "net_profit_pln": 170,  # 500 - (250 + 30 + 50) = 170
                "roi_percentage": 51,
                "is_profitable": True,
                "recommendation_reason": "Wymiana lasera KES-496 i czyszczenie dają 170 zł zysku na czysto."
            })
        }
    }

    def mock_handler(request: httpx.Request) -> httpx.Response:
        req_body = json.loads(request.content.decode("utf-8"))
        assert req_body["model"] == "qwen2.5:14b"
        assert req_body["format"] == "json"
        return httpx.Response(200, json=ollama_response)

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)

    result = evaluate_listing_with_ollama(
        mock_listing,
        client=client,
        ollama_url="http://mock-ollama:11434",
        model_name="qwen2.5:14b",
        profit_threshold=100.0,
        shipping_cost=30.0
    )

    assert result.item_title == "PS4 Slim 500GB"
    assert result.category == "Konsole"
    assert result.estimated_parts_cost_pln == 50
    assert result.estimated_resale_price_pln == 500
    assert result.net_profit_pln == 170
    assert result.is_profitable is True

def test_evaluate_listing_forced_rejection_blacklisted_macbook_2011():
    mock_listing = Listing(
        id="test_macbook_2011",
        title="MacBook Pro 15 2011 i7 uszkodzona grafika",
        price=200.0,
        currency="PLN",
        description="Paski na ekranie, uszkodzony GPU Radeon 2011.",
        url="https://example.com/macbook2011",
        platform="Vinted",
        category="Laptopy"
    )

    ollama_response = {
        "message": {
            "content": json.dumps({
                "item_title": "MacBook Pro 15 2011",
                "category": "Laptopy",
                "detected_fault": "Uszkodzona dedykowana karta graficzna Radeon AMD",
                "difficulty_level": "Trudna",
                "estimated_parts_cost_pln": 100,
                "estimated_resale_price_pln": 600,
                "net_profit_pln": 270,
                "roi_percentage": 82,
                "is_profitable": True,
                "recommendation_reason": "Naprawa karty graficznej."
            })
        }
    }

    transport = httpx.MockTransport(lambda req: httpx.Response(200, json=ollama_response))
    client = httpx.Client(transport=transport)

    result = evaluate_listing_with_ollama(mock_listing, client=client, profit_threshold=100.0)

    # Forced False due to 2011 MacBook Pro blacklist pattern
    assert result.is_profitable is False

def test_evaluate_listing_forced_rejection_untested_or_liquid_damage():
    mock_listing = Listing(
        id="test_flooded_xbox",
        title="Xbox 360 Xenon zalana wodą nietestowany",
        price=50.0,
        currency="PLN",
        description="Konsola po zalaniu płynem, stan nieznany nietestowany.",
        url="https://example.com/xbox_zalana",
        platform="Vinted",
        category="Konsole"
    )

    ollama_response = {
        "message": {
            "content": json.dumps({
                "item_title": "Xbox 360 Xenon",
                "category": "Konsole",
                "detected_fault": "Stan nieznany, zalany płynem",
                "difficulty_level": "Trudna",
                "estimated_parts_cost_pln": 30,
                "estimated_resale_price_pln": 200,
                "net_profit_pln": 90,
                "roi_percentage": 80,
                "is_profitable": True,
                "recommendation_reason": "Zalana konsola."
            })
        }
    }

    transport = httpx.MockTransport(lambda req: httpx.Response(200, json=ollama_response))
    client = httpx.Client(transport=transport)

    result = evaluate_listing_with_ollama(mock_listing, client=client, profit_threshold=100.0)

    # Forced False due to liquid damage and Xenon blacklist
    assert result.is_profitable is False
