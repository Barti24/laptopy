import logging
from typing import List, Dict, Any
import httpx
from models import Listing
from config import DEFAULT_HEADERS

logger = logging.getLogger(__name__)

VINTED_API_URL = "https://www.vinted.pl/api/v2/catalog/items"

def parse_vinted_json(data: Dict[str, Any]) -> List[Listing]:
    """Parse JSON response from Vinted catalog API."""
    listings: List[Listing] = []
    items = data.get("items", [])

    for item in items:
        try:
            item_id = str(item.get("id"))
            title = item.get("title", "").strip()
            price_val = item.get("price") or item.get("total_item_price") or (item.get("price_numeric") if "price_numeric" in item else None)

            # If price is dict or float/str
            if isinstance(price_val, dict):
                price_amount = float(price_val.get("amount", 0))
                currency = price_val.get("currency_code", "PLN")
            elif price_val is not None:
                price_amount = float(price_val)
                currency = item.get("currency", "PLN")
            else:
                continue

            url = item.get("url", "")
            if url and not url.startswith("http"):
                url = f"https://www.vinted.pl{url}"

            # Fetch description or fallback to title
            description = item.get("description") or title

            # Photo URL
            photos = item.get("photos", [])
            image_url = None
            if photos and isinstance(photos, list):
                first_photo = photos[0]
                if isinstance(first_photo, dict):
                    image_url = first_photo.get("url") or first_photo.get("full_size_url")

            if item_id and title:
                listings.append(Listing(
                    id=f"vinted_{item_id}",
                    title=title,
                    price=price_amount,
                    currency=currency,
                    description=description,
                    url=url,
                    platform="Vinted",
                    image_url=image_url
                ))
        except Exception as e:
            logger.debug(f"Error parsing Vinted item: {e}")

    return listings

def fetch_vinted_listings(client: httpx.Client = None, search_text: str = "laptop") -> List[Listing]:
    """Fetch laptop listings from Vinted API with session initialization."""
    should_close = False
    if client is None:
        client = httpx.Client(headers=DEFAULT_HEADERS, timeout=10.0, follow_redirects=True)
        should_close = True

    try:
        # Vinted API requires session cookies established by visiting main page first
        try:
            client.get("https://www.vinted.pl/")
        except Exception as e:
            logger.debug(f"Vinted initial session request warning: {e}")

        params = {
            "search_text": search_text,
            "order": "newest_first",
            "page": 1,
            "per_page": 20
        }

        response = client.get(VINTED_API_URL, params=params)
        response.raise_for_status()
        return parse_vinted_json(response.json())
    except Exception as e:
        logger.error(f"Error fetching Vinted listings: {e}")
        return []
    finally:
        if should_close:
            client.close()
