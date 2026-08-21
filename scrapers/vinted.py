import logging
import random
import time
from typing import List, Dict, Any, Optional, Set
from curl_cffi import requests as curl_requests
from models import Listing

logger = logging.getLogger(__name__)

VINTED_API_URL = "https://www.vinted.pl/api/v2/catalog/items"

VINTED_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.vinted.pl/",
    "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin"
}

MAX_PAGES_DEFAULT = 5
MAX_403_RETRIES = 2

def bootstrap_vinted_session(session: curl_requests.Session) -> bool:
    """Visit Vinted homepage to obtain fresh session cookies and CSRF headers."""
    logger.info("Bootstrapping Vinted session cookies from https://www.vinted.pl/...")
    try:
        init_headers = dict(VINTED_HEADERS)
        init_headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        init_headers["Sec-Fetch-Dest"] = "document"
        init_headers["Sec-Fetch-Mode"] = "navigate"
        init_headers["Sec-Fetch-Site"] = "none"
        init_headers["Sec-Fetch-User"] = "?1"

        response = session.get("https://www.vinted.pl/", headers=init_headers, timeout=15)
        response.raise_for_status()
        logger.info("Successfully bootstrapped Vinted session cookies.")
        return True
    except Exception as e:
        logger.warning(f"Failed to bootstrap Vinted session cookies: {e}")
        return False

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
    """Fetch a single page of listings from Vinted API with cookie bootstrapping and 403 retries."""
    should_close = False
    if session is None:
        session = curl_requests.Session(impersonate="chrome120")
        should_close = True

    try:
        # Bootstrap session if no cookies present
        if not session.cookies:
            bootstrap_vinted_session(session)

        params = {
            "search_text": search_text,
            "order": "newest_first",
            "page": page,
            "per_page": per_page
        }

        for attempt in range(MAX_403_RETRIES + 1):
            try:
                response = session.get(VINTED_API_URL, params=params, headers=VINTED_HEADERS, timeout=15)

                # If 403 Forbidden, refresh session cookies and retry
                if response.status_code == 403 and attempt < MAX_403_RETRIES:
                    logger.warning(f"HTTP 403 Forbidden on page {page} attempt {attempt+1}/{MAX_403_RETRIES+1}. Refreshing Vinted session cookies...")
                    time.sleep(random.uniform(2.0, 4.0))
                    bootstrap_vinted_session(session)
                    continue

                response.raise_for_status()
                return parse_vinted_json(response.json(), category=category)

            except curl_requests.HTTPError as e:
                status_code = getattr(e.response, "status_code", None) if hasattr(e, "response") else None
                if status_code == 403 and attempt < MAX_403_RETRIES:
                    logger.warning(f"HTTP 403 Forbidden exception on page {page} attempt {attempt+1}. Refreshing session...")
                    time.sleep(random.uniform(2.0, 4.0))
                    bootstrap_vinted_session(session)
                    continue
                else:
                    logger.error(f"Error fetching Vinted page {page} for '{search_text}': {e}")
                    return []
            except Exception as e:
                logger.error(f"Unexpected error fetching Vinted page {page} for '{search_text}': {e}")
                return []

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
    Incremental deep scan with random throttling delays:
    1. Fetch Page 1 first (newest items).
    2. Add random delay (1.5 - 3.0s) between pages.
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
            if page > 1:
                delay = random.uniform(1.5, 3.0)
                logger.info(f"Throttling delay: waiting {delay:.2f}s before fetching page {page}...")
                time.sleep(delay)

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

            new_on_page = [item for item in page_items if item.id not in seen_ids]
            logger.info(f"Page {page} returned {len(page_items)} items ({len(new_on_page)} unseen).")

            if len(new_on_page) == 0:
                logger.info(f"Hit existing history boundary on page {page} (all items already seen). Stopping deep scan.")
                break

        return all_scraped_listings

    finally:
        if should_close:
            session.close()
