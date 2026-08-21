import logging
from typing import List, Dict, Any, Optional, Set
from curl_cffi import requests as curl_requests
from models import Listing

logger = logging.getLogger(__name__)

VINTED_API_URL = "https://www.vinted.pl/api/v2/catalog/items"

VINTED_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
}

MAX_PAGES_DEFAULT = 5

def parse_vinted_json(data: Dict[str, Any], category: str = "Inne") -> List[Listing]:
    """Parse JSON response from Vinted catalog API."""
    listings: List[Listing] = []
    items = data.get("items", [])

    for item in items:
        try:
            item_id = str(item.get("id"))
            title = item.get("title", "").strip()
            price_val = item.get("price") or item.get("total_item_price") or (item.get("price_numeric") if "price_numeric" in item else None)

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

            description = item.get("description") or title

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
                    category=category,
                    image_url=image_url
                ))
        except Exception as e:
            logger.debug(f"Error parsing Vinted item: {e}")

    return listings

def fetch_vinted_listings(
    session: Optional[curl_requests.Session] = None,
    search_text: str = "laptop",
    category: str = "Inne",
    page: int = 1,
    per_page: int = 20
) -> List[Listing]:
    """Fetch a single page of listings from Vinted API using curl_cffi."""
    should_close = False
    if session is None:
        session = curl_requests.Session(impersonate="chrome120")
        should_close = True

    try:
        # Visit main page to obtain cookies (_vinted_fr_session) if not already set
        if not session.cookies:
            try:
                init_headers = dict(VINTED_HEADERS)
                init_headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
                session.get("https://www.vinted.pl/", headers=init_headers, timeout=15)
            except Exception as e:
                logger.debug(f"Vinted initial session request warning: {e}")

        params = {
            "search_text": search_text,
            "order": "newest_first",
            "page": page,
            "per_page": per_page
        }

        response = session.get(VINTED_API_URL, params=params, headers=VINTED_HEADERS, timeout=15)
        response.raise_for_status()
        return parse_vinted_json(response.json(), category=category)
    except Exception as e:
        logger.error(f"Error fetching Vinted page {page} for '{search_text}': {e}")
        return []
    finally:
        if should_close:
            session.close()

def fetch_vinted_listings_deep(
    session: Optional[curl_requests.Session] = None,
    search_text: str = "laptop",
    category: str = "Inne",
    seen_ids: Set[str] = None,
    max_pages: int = MAX_PAGES_DEFAULT
) -> List[Listing]:
    """
    Incremental deep scan:
    1. Fetch Page 1 first (newest items).
    2. If Page 1 contains unseen items (not in seen_ids), continue to Page 2, 3...
    3. Stop when all items on a page are already in seen_ids, or max_pages limit is reached.
    """
    if seen_ids is None:
        seen_ids = set()

    should_close = False
    if session is None:
        session = curl_requests.Session(impersonate="chrome120")
        should_close = True

    all_scraped_listings: List[Listing] = []

    try:
        for page in range(1, max_pages + 1):
            logger.info(f"Fetching Vinted [{category}] page {page}/{max_pages} for search '{search_text}'...")
            page_items = fetch_vinted_listings(
                session=session,
                search_text=search_text,
                category=category,
                page=page
            )

            if not page_items:
                logger.info(f"Page {page} returned no items. Ending deep scan for [{category}].")
                break

            all_scraped_listings.extend(page_items)

            # Check how many items on this page are brand new (unseen)
            new_on_page = [item for item in page_items if item.id not in seen_ids]
            logger.info(f"Page {page} returned {len(page_items)} items ({len(new_on_page)} unseen).")

            # If no unseen items on this page, stop paginating deeper
            if len(new_on_page) == 0:
                logger.info(f"Hit existing history boundary on page {page} (all items already seen). Stopping deep scan.")
                break

        return all_scraped_listings

    finally:
        if should_close:
            session.close()
