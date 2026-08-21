import re
import json
import logging
from typing import List, Optional
from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests
from models import Listing
from config import DEFAULT_HEADERS

logger = logging.getLogger(__name__)

DEFAULT_OLX_URL = "https://www.olx.pl/elektronika/komputery/laptopy/"

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
    "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1"
}

def parse_olx_html(html_content: str, category: str = "Inne") -> List[Listing]:
    """Parse HTML content or embedded __PRERENDERED_STATE__ JSON from OLX search page."""
    listings: List[Listing] = []

    state_match = re.search(r'window\.__PRERENDERED_STATE__\s*=\s*(\{.*?\});', html_content, re.DOTALL)
    if state_match:
        try:
            state_data = json.loads(state_match.group(1))
            ads_data = None
            if "ad" in state_data and "adData" in state_data["ad"]:
                ads_data = state_data["ad"]["adData"]
            elif "search" in state_data and "data" in state_data["search"]:
                ads_data = state_data["search"]["data"]

            if isinstance(ads_data, list):
                for item in ads_data:
                    try:
                        ad_id = str(item.get("id"))
                        title = item.get("title", "").strip()
                        price_data = item.get("price", {})
                        price_val = price_data.get("value") or price_data.get("regularPrice", {}).get("value")
                        if price_val is None:
                            continue
                        price = float(price_val)
                        description = item.get("description", "") or title
                        url = item.get("url", "")
                        if url and not url.startswith("http"):
                            url = "https://www.olx.pl" + url

                        photos = item.get("photos", [])
                        image_url = photos[0].get("link", "").replace("{width}", "800").replace("{height}", "600") if photos else None

                        if ad_id and title and price is not None:
                            listings.append(Listing(
                                id=f"olx_{ad_id}",
                                title=title,
                                price=price,
                                currency="PLN",
                                description=description,
                                url=url,
                                platform="OLX",
                                category=category,
                                image_url=image_url
                            ))
                    except Exception as e:
                        logger.debug(f"Error parsing OLX state item: {e}")
                if listings:
                    return listings
        except Exception as e:
            logger.debug(f"Could not parse window.__PRERENDERED_STATE__: {e}")

    soup = BeautifulSoup(html_content, "html.parser")
    cards = soup.select('div[data-cy="l-card"]')

    for card in cards:
        try:
            link_elem = card.select_one('a[href]')
            if not link_elem:
                continue
            href = link_elem.get('href', '')
            if not href:
                continue
            url = href if href.startswith("http") else f"https://www.olx.pl{href}"

            title_elem = card.select_one('h6, h4, [data-cy="ad-card-title"]')
            title = title_elem.get_text(strip=True) if title_elem else ""
            if not title:
                continue

            price_elem = card.select_one('[data-testid="ad-price"]')
            if not price_elem:
                continue
            price_text = price_elem.get_text(strip=True)
            price_nums = re.sub(r'[^\d,.]', '', price_text.replace(' ', '')).replace(',', '.')
            if not price_nums:
                continue
            price = float(price_nums)

            id_match = re.search(r'ID([a-zA-Z0-9]+)\.html', url) or re.search(r'-ID([a-zA-Z0-9]+)', url)
            if id_match:
                listing_id = f"olx_{id_match.group(1)}"
            else:
                listing_id = f"olx_{hash(url)}"

            img_elem = card.select_one('img')
            image_url = img_elem.get('src') if img_elem else None

            listings.append(Listing(
                id=listing_id,
                title=title,
                price=price,
                currency="PLN",
                description=f"Tytuł: {title}",
                url=url,
                platform="OLX",
                category=category,
                image_url=image_url
            ))
        except Exception as e:
            logger.debug(f"Error parsing OLX HTML card: {e}")

    return listings

def fetch_olx_listings(session: Optional[curl_requests.Session] = None, url: str = DEFAULT_OLX_URL, category: str = "Inne") -> List[Listing]:
    """Fetch listings from OLX using curl_cffi with chrome120 impersonation to bypass 403."""
    should_close = False
    if session is None:
        session = curl_requests.Session(impersonate="chrome120")
        should_close = True

    try:
        response = session.get(url, headers=BROWSER_HEADERS, timeout=15)
        response.raise_for_status()
        return parse_olx_html(response.text, category=category)
    except Exception as e:
        logger.error(f"Error fetching OLX listings from {url}: {e}")
        return []
    finally:
        if should_close:
            session.close()
