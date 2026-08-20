import pytest
import json
import httpx
from models import Listing
from ollama_evaluator import evaluate_listing_with_ollama

def test_evaluate_listing_repair_profitable():
    mock_listing = Listing(
        id="test_console_1",
        title="PS4 Slim 500GB nie czyta płyt głośno chodzi",
        price=250.0,
        currency="PLN",
        description="Konsola włącza się, ale napęd nie pobiera płyt. Wymaga czyszczenia.",
        url="https://example.com/ps4",
        platform="OLX",
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

def test_evaluate_listing_repair_unprofitable_gpu_die():
    mock_listing = Listing(
        id="test_gpu_2",
        title="RTX 3070 czarny ekran artefakty",
        price=600.0,
        currency="PLN",
        description="Karta po spięciu, czarny obraz.",
        url="https://example.com/rtx3070",
        platform="OLX",
        category="Karty graficzne"
    )

    ollama_response = {
        "message": {
            "content": json.dumps({
                "item_title": "RTX 3070",
                "category": "Karty graficzne",
                "detected_fault": "Uszkodzenie rdzenia GPU / pamięci VRAM",
                "difficulty_level": "Trudna",
                "estimated_parts_cost_pln": 400,
                "estimated_market_value_working_pln": 1000,
                "net_profit_pln": -15,
                "roi_percentage": -1,
                "is_profitable": False,
                "recommendation_reason": "Wysokie ryzyko uszkodzenia rdzenia BGA, wymiana rdzenia nieopłacalna."
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

    assert result.is_profitable is False
    assert result.net_profit_pln < 100
    assert "nieopłacalna" in result.recommendation_reason
