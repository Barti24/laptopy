import pytest
import json
import httpx
from models import Listing
from ollama_evaluator import evaluate_listing_with_ollama

def test_evaluate_listing_with_ollama_success():
    mock_listing = Listing(
        id="test_1",
        title="Dell Latitude 5420 i5 11 gen 16GB RAM",
        price=1000.0,
        currency="PLN",
        description="Laptop w pełni sprawny z ładowarką.",
        url="https://example.com/test",
        platform="OLX"
    )

    ollama_response = {
        "message": {
            "content": json.dumps({
                "estimated_market_value": 1300.0,
                "estimated_profit": 300.0,
                "reasoning": "Rynkowa cena tego modelu to ok. 1300 PLN. Zysk wynosi 300 PLN."
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
        profit_threshold=150.0
    )

    assert result.estimated_market_value == 1300.0
    assert result.estimated_profit == 300.0
    assert result.is_profitable is True
    assert "1300 PLN" in result.reasoning

def test_evaluate_listing_with_ollama_below_threshold():
    mock_listing = Listing(
        id="test_2",
        title="Stary Asus i3 3gen",
        price=400.0,
        currency="PLN",
        description="Stary laptop, mało pamięci.",
        url="https://example.com/test2",
        platform="OLX"
    )

    ollama_response = {
        "message": {
            "content": json.dumps({
                "estimated_market_value": 450.0,
                "estimated_profit": 50.0,
                "reasoning": "Niska opłacalność, zysk tylko 50 PLN."
            })
        }
    }

    transport = httpx.MockTransport(lambda req: httpx.Response(200, json=ollama_response))
    client = httpx.Client(transport=transport)

    result = evaluate_listing_with_ollama(
        mock_listing,
        client=client,
        profit_threshold=150.0
    )

    assert result.estimated_market_value == 450.0
    assert result.estimated_profit == 50.0
    assert result.is_profitable is False
