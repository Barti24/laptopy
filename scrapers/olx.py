import re
import json
import logging
from typing import List
import httpx
from bs4 import BeautifulSoup
from models import Listing
from config import DEFAULT_HEADERS

logger = logging.getLogger(__name__)

OLX_LAPTOPS_URL = "https://www.olx.pl/elektronika/komputery/laptopy/"

def parse_olx_html(html_content: str) -> List[Listing]:
    """Parse HTML content or embedded __PRERENDERED_STATE__ JSON from OLX search page."""
    listings: List[Listing] = []

    # Try parsing embedded script state if available
    state_match = re.search(r'window\.__PRERENDERED_STATE__\s*=\s*(\{.*?\});', html_content, re.DOTALL)
    if state_match:
        try:
            state_data = json.loads(state_match.group(1))
            # Try finding ads in state_data
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
                                image_url=image_url
                            ))
                    except Exception as e:
                        logger.debug(f"Error parsing OLX state item: {e}")
                if listings:
                    return listings
        except Exception as e:
            logger.debug(f"Could not parse window.__PRERENDERED_STATE__: {e}")

    # Fallback to BeautifulSoup HTML DOM parsing
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
            # Extract numbers from price string e.g. "1 200 zł" -> 1200.0
            price_nums = re.sub(r'[^\d,.]', '', price_text.replace(' ', '')).replace(',', '.')
            if not price_nums:
                continue
            price = float(price_nums)

            # Generate listing ID from URL or card ID attribute
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
                image_url=image_url
            ))
        except Exception as e:
            logger.debug(f"Error parsing OLX HTML card: {e}")

    return listings

def fetch_olx_listings(client: httpx.Client = None, url: str = OLX_LAPTOPS_URL) -> List[Listing]:
    """Fetch laptop listings from OLX."""
    should_close = False
    if client is None:
        client = httpx.Client(headers=DEFAULT_HEADERS, timeout=10.0, follow_redirects=True)
        should_close = True

    try:
        response = client.get(url)
        response.raise_for_status()
        return parse_olx_html(response.text)
    except Exception as e:
        logger.error(f"Error fetching OLX listings from {url}: {e}")
        return []
    finally:
        if should_close:
            client.close()
