import pytest
from scrapers.olx import parse_olx_html
from scrapers.vinted import parse_vinted_json

def test_parse_olx_html_prerendered_state():
    html_sample = """
    <html>
    <head>
    <script>
    window.__PRERENDERED_STATE__ = {
        "ad": {
            "adData": [
                {
                    "id": "12345",
                    "title": "Laptop Lenovo ThinkPad T14 i5 16GB",
                    "price": {"value": 1200},
                    "description": "Świetny laptop biznesowy w dobrym stanie.",
                    "url": "https://www.olx.pl/d/oferta/laptop-lenovo-thinkpad-t14-ID12345.html",
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
    listings = parse_olx_html(html_sample)
    assert len(listings) == 1
    listing = listings[0]
    assert listing.id == "olx_12345"
    assert listing.title == "Laptop Lenovo ThinkPad T14 i5 16GB"
    assert listing.price == 1200.0
    assert listing.platform == "OLX"
    assert listing.currency == "PLN"
    assert listing.image_url == "https://img.olx.pl/photos/800x600.jpg"

def test_parse_olx_html_dom_fallback():
    html_sample = """
    <div data-cy="l-card">
        <a href="/d/oferta/laptop-hp-probook-ID999.html">
            <h6 class="title">Laptop HP ProBook 450 G8</h6>
            <span data-testid="ad-price">850 zł</span>
        </a>
    </div>
    """
    listings = parse_olx_html(html_sample)
    assert len(listings) == 1
    listing = listings[0]
    assert listing.id == "olx_999"
    assert listing.title == "Laptop HP ProBook 450 G8"
    assert listing.price == 850.0
    assert listing.platform == "OLX"

def test_parse_vinted_json():
    json_sample = {
        "items": [
            {
                "id": 987654,
                "title": "MacBook Air M1 8GB 256GB Space Gray",
                "price": {"amount": "2100.00", "currency_code": "PLN"},
                "description": "Laptop w stanie idealnym, bateria 92%.",
                "url": "/items/987654-macbook-air-m1",
                "photos": [{"url": "https://images1.vinted.net/item_1.jpg"}]
            }
        ]
    }
    listings = parse_vinted_json(json_sample)
    assert len(listings) == 1
    listing = listings[0]
    assert listing.id == "vinted_987654"
    assert listing.title == "MacBook Air M1 8GB 256GB Space Gray"
    assert listing.price == 2100.0
    assert listing.url == "https://www.vinted.pl/items/987654-macbook-air-m1"
    assert listing.platform == "Vinted"
    assert listing.image_url == "https://images1.vinted.net/item_1.jpg"
