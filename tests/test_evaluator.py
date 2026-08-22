import pytest
import json
import httpx
from models import Listing
from ollama_evaluator import evaluate_listing_with_ollama
from main import passes_pre_filter

def test_passes_pre_filter_exclude_toys_overrides_cheap_pass():
    listing = Listing(
        id="test_cheap_toy",
        title="Laptop zabaweczka fisher price edukacyjny dlay dzieci barbie",
        price=15.0,  # Extremely cheap, BUT matches toy blacklist!
        currency="PLN",
        description="Grający komputerek interaktywny fisher price.",
        url="https://example.com/cheaptoy",
        platform="Vinted",
        category="Laptopy"
    )
    # MUST be rejected at Step 2 despite low price
    assert passes_pre_filter(listing, max_price=1200.0) is False

def test_passes_pre_filter_open_gate_passes_clean_item():
    listing = Listing(
        id="test_1",
        title="Laptop Lenovo ThinkPad T14 sprawny jak nowy",
        price=500.0,
        currency="PLN",
        description="Laptop działa idealnie, stan świetny.",
        url="https://example.com/1",
        platform="Vinted",
        category="Laptopy"
    )
    # Passes open pre-filter to Ollama AI evaluation even without fault keywords!
    assert passes_pre_filter(listing, max_price=1200.0) is True

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
    assert passes_pre_filter(listing, max_price=1200.0) is False

def test_evaluate_listing_market_search_integration(monkeypatch):
    mock_listing = Listing(
        id="test_search_1",
        title="Dell Latitude 5420 i5 11gen uszkodzony ekran",
        price=300.0,
        currency="PLN",
        description="Laptop działa pod zewnętrznym monitorem HDMI.",
        url="https://example.com/dell5420",
        platform="Vinted",
        category="Laptopy"
    )

    def mock_search_market_prices(title: str, max_results: int = 3) -> str:
        return "1. [Dell Latitude 5420 i5 11gen] - Cena Allegro ok. 1200 PLN sprawny"

    monkeypatch.setattr("ollama_evaluator.search_market_prices", mock_search_market_prices)

    captured_prompt = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        user_msg = body["messages"][1]["content"]
        captured_prompt.append(user_msg)
        assert "WYNIKI Z WYSZUKIWARKI RYNKOWEJ" in user_msg
        assert "Dell Latitude 5420 i5 11gen" in user_msg

        ollama_response = {
            "message": {
                "content": json.dumps({
                    "item_title": "Dell Latitude 5420",
                    "category": "Laptopy",
                    "deal_type": "OKAZJA_NAPRAWA",
                    "deal_score": 9,
                    "estimated_market_value": 1200,
                    "negotiation_target": 250,
                    "market_liquidity": "BARDZO SZYBKO",
                    "risk_assessment": "NISKIE - sprawna płyta po HDMI",
                    "salvage_value": 500,
                    "fault_analysis": "Uszkodzona matryca FHD 14 cali",
                    "repair_difficulty": "ŁATWA",
                    "repair_steps": ["1. Wymiana matrycy 14 cali FHD"],
                    "estimated_parts_cost": 200,
                    "estimated_net_profit": 680,
                    "reasoning": "Tania wymiana matrycy przy wysokiej wartości rynkowej z Allegro."
                })
            }
        }
        return httpx.Response(200, json=ollama_response)

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)

    result = evaluate_listing_with_ollama(mock_listing, client=client, search_market=True)

    assert result.deal_type == "OKAZJA_NAPRAWA"
    assert result.deal_score == 9
    assert result.estimated_market_value == 1200
    assert result.estimated_parts_cost == 200
    assert result.estimated_net_profit == 680
    assert result.is_profitable is True
    assert len(captured_prompt) == 1

def test_evaluate_listing_low_market_value_rejection():
    mock_listing = Listing(
        id="test_gadget_1",
        title="Mały głośniczek brelok",
        price=15.0,
        currency="PLN",
        description="Mały brelok głośnikowy.",
        url="https://example.com/brelok",
        platform="Vinted",
        category="Sprzęt Audio"
    )

    ollama_response = {
        "message": {
            "content": json.dumps({
                "item_title": "Brelok głośnik",
                "category": "Sprzęt Audio",
                "deal_type": "OKAZJA_FLIP",
                "deal_score": 7,
                "estimated_market_value": 35,  # Below 50 PLN
                "negotiation_target": 10,
                "market_liquidity": "NISKA PŁYNNOŚĆ",
                "risk_assessment": "NISKIE - gadżet",
                "salvage_value": 5,
                "fault_analysis": "Brak usterki",
                "repair_difficulty": "Brak",
                "repair_steps": [],
                "estimated_parts_cost": 0,
                "estimated_net_profit": 0,
                "reasoning": "Tani brelok."
            })
        }
    }

    transport = httpx.MockTransport(lambda req: httpx.Response(200, json=ollama_response))
    client = httpx.Client(transport=transport)

    result = evaluate_listing_with_ollama(mock_listing, client=client, search_market=False)

    # Forcing BRAK_ZYSKU because market_value 35 PLN < 50 PLN
    assert result.deal_type == "BRAK_ZYSKU"
    assert result.is_profitable is False
