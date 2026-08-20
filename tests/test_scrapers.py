import pytest
from scrapers.olx import parse_olx_html
from scrapers.vinted import parse_vinted_json

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
