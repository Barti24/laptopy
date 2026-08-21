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

def test_evaluate_listing_repair_profitable():
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
                "detected_fault": "Uszkodzony laser/napęd oraz zapchane chłodzenie",
                "difficulty_level": "Prosta",
                "estimated_parts_cost_pln": 50,
                "estimated_market_value_working_pln": 500,
                "net_profit_pln": 185,
                "roi_percentage": 58,
                "is_profitable": True,
                "recommendation_reason": "Prosta wymiana lasera i czyszczenie dają 185 zł zysku na czysto."
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
        profit_threshold=100.0
    )

    assert result.item_title == "PS4 Slim 500GB"
    assert result.category == "Konsole"
    assert result.detected_fault == "Uszkodzony laser/napęd oraz zapchane chłodzenie"
    assert result.difficulty_level == "Prosta"
    assert result.estimated_parts_cost_pln == 50
    assert result.estimated_market_value_working_pln == 500
    assert result.net_profit_pln == 185
    assert result.roi_percentage == 58
    assert result.is_profitable is True
    assert "185 zł zysku" in result.recommendation_reason

def test_evaluate_listing_forced_non_profitable_when_no_fault():
    mock_listing = Listing(
        id="test_no_fault_1",
        title="Konsola PS4 sprawna gierki uszkodzony kabel",
        price=200.0,
        currency="PLN",
        description="Konsola działa idealnie, po prostu brak kabla HDMI.",
        url="https://example.com/ps4sprawna",
        platform="Vinted",
        category="Konsole"
    )

    ollama_response = {
        "message": {
            "content": json.dumps({
                "item_title": "PS4",
                "category": "Konsole",
                "detected_fault": "Brak usterki, sprzęt w pełni sprawny",
                "difficulty_level": "Prosta",
                "estimated_parts_cost_pln": 10,
                "estimated_market_value_working_pln": 500,
                "net_profit_pln": 275,
                "roi_percentage": 122,
                "is_profitable": True,  # LLM erroneously returned True
                "recommendation_reason": "Konsola jest sprawna."
            })
        }
    }

    transport = httpx.MockTransport(lambda req: httpx.Response(200, json=ollama_response))
    client = httpx.Client(transport=transport)

    result = evaluate_listing_with_ollama(
        mock_listing,
        client=client,
        profit_threshold=100.0
    )

    # Should be forced to False because detected_fault indicates no fault
    assert result.is_profitable is False
