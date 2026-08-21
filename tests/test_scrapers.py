import pytest
from scrapers.olx import parse_olx_html
from scrapers.vinted import parse_vinted_json, fetch_vinted_listings_deep, bootstrap_vinted_session, fetch_vinted_listings
from models import Listing
from curl_cffi import requests as curl_requests

def test_parse_olx_html_prerendered_state_with_category():
    html_sample = """
    <html>
    <head>
    <script>
    window.__PRERENDERED_STATE__ = {
        "ad": {
            "adData": [
                {
                    "id": "12345",
                    "title": "PS4 Slim 500GB głośno chodzi uszkodzony napęd",
                    "price": {"value": 300},
                    "description": "Konsola działa ale napęd nie czyta płyt.",
                    "url": "https://www.olx.pl/d/oferta/ps4-slim-ID12345.html",
                    "photos": [{"link": "https://img.olx.pl/photos/{width}x{height}.jpg"}]
                }
            ]
        }
    };
    </script>
    </head>
    <body></body>
    </html>
    """
    listings = parse_olx_html(html_sample, category="Konsole")
    assert len(listings) == 1
    listing = listings[0]
    assert listing.id == "olx_12345"
    assert listing.title == "PS4 Slim 500GB głośno chodzi uszkodzony napęd"
    assert listing.price == 300.0
    assert listing.platform == "OLX"
    assert listing.category == "Konsole"
    assert listing.currency == "PLN"
    assert listing.image_url == "https://img.olx.pl/photos/800x600.jpg"

def test_parse_olx_html_dom_fallback_with_category():
    html_sample = """
    <div data-cy="l-card">
        <a href="/d/oferta/karta-rtx-2060-artefakty-ID999.html">
            <h6 class="title">RTX 2060 6GB artefakty</h6>
            <span data-testid="ad-price">200 zł</span>
        </a>
    </div>
    """
    listings = parse_olx_html(html_sample, category="Karty graficzne")
    assert len(listings) == 1
    listing = listings[0]
    assert listing.id == "olx_999"
    assert listing.title == "RTX 2060 6GB artefakty"
    assert listing.price == 200.0
    assert listing.category == "Karty graficzne"
    assert listing.platform == "OLX"

def test_parse_vinted_json_with_category():
    json_sample = {
        "items": [
            {
                "id": 987654,
                "title": "Drukarka 3D Ender 3 zatkana dysza",
                "price": {"amount": "250.00", "currency_code": "PLN"},
                "description": "Ender 3 zatkana dysza, poza tym sprawna.",
                "url": "/items/987654-ender-3",
                "photos": [{"url": "https://images1.vinted.net/item_1.jpg"}]
            }
        ]
    }
    listings = parse_vinted_json(json_sample, category="Drukarki 3D")
    assert len(listings) == 1
    listing = listings[0]
    assert listing.id == "vinted_987654"
    assert listing.title == "Drukarka 3D Ender 3 zatkana dysza"
    assert listing.price == 250.0
    assert listing.category == "Drukarki 3D"
    assert listing.url == "https://www.vinted.pl/items/987654-ender-3"
    assert listing.platform == "Vinted"

def test_vinted_403_retry_and_bootstrap(monkeypatch):
    class MockResponse:
        def __init__(self, status_code, json_data=None):
            self.status_code = status_code
            self._json_data = json_data or {}

        def raise_for_status(self):
            if self.status_code >= 400:
                raise curl_requests.HTTPError(f"HTTP {self.status_code}", response=self)

        def json(self):
            return self._json_data

    attempts = {"count": 0}

    class MockSession:
        def __init__(self):
            self.cookies = {"_vinted_fr_session": "test_cookie"}

        def get(self, url, params=None, headers=None, timeout=15):
            if "api/v2/catalog/items" in url:
                attempts["count"] += 1
                if attempts["count"] == 1:
                    return MockResponse(403)
                return MockResponse(200, {"items": [{"id": 111, "title": "Test Laptop", "price": 100}]})
            return MockResponse(200)

        def close(self):
            pass

    mock_session = MockSession()
    items = fetch_vinted_listings(session=mock_session, search_text="laptop")
    assert len(items) == 1
    assert items[0].id == "vinted_111"
    assert attempts["count"] == 2

def test_fetch_vinted_listings_deep_stop_on_seen_boundary(monkeypatch):
    page1_data = {
        "items": [
            {"id": 101, "title": "Laptop 101 uszkodzony", "price": 100},
            {"id": 102, "title": "Laptop 102 uszkodzony", "price": 120}
        ]
    }
    page2_data = {
        "items": [
            {"id": 103, "title": "Laptop 103 uszkodzony", "price": 130},
            {"id": 104, "title": "Laptop 104 uszkodzony", "price": 140}
        ]
    }

    pages_called = []

    def mock_fetch_vinted_listings(session=None, search_text="laptop", category="Laptopy", page=1, per_page=20):
        pages_called.append(page)
        if page == 1:
            return parse_vinted_json(page1_data, category=category)
        elif page == 2:
            return parse_vinted_json(page2_data, category=category)
        return []

    monkeypatch.setattr("scrapers.vinted.fetch_vinted_listings", mock_fetch_vinted_listings)

    seen_ids = set()
    result = fetch_vinted_listings_deep(search_text="laptop", category="Laptopy", seen_ids=seen_ids, max_pages=3)
    assert len(result) == 4
    assert pages_called == [1, 2, 3]

    pages_called.clear()
    seen_ids_existing = {"vinted_101", "vinted_102"}
    result_existing = fetch_vinted_listings_deep(search_text="laptop", category="Laptopy", seen_ids=seen_ids_existing, max_pages=5)
    assert len(result_existing) == 2
    assert pages_called == [1]
