import logging
from typing import List, Dict, Any
from ddgs import DDGS

logger = logging.getLogger(__name__)

def search_market_prices(title: str, max_results: int = 3) -> str:
    """
    Search DuckDuckGo for top 3 market pricing results for the given item title.
    Query: f"{title} cena OLX Allegro"
    Returns a formatted string containing snippets and titles from web results.
    """
    query = f"{title} cena OLX Allegro"
    formatted_results: List[str] = []

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            for i, item in enumerate(results, 1):
                item_title = item.get("title", "")
                snippet = item.get("body", "") or item.get("snippet", "")
                url = item.get("href", "")
                if item_title or snippet:
                    formatted_results.append(f"{i}. [{item_title}] - {snippet} ({url})")
    except Exception as e:
        logger.warning(f"Error performing DuckDuckGo market price search for '{title}': {e}")
        return "Brak wyników z wyszukiwarki (błąd wyszukiwania)."

    if not formatted_results:
        return "Brak wyników z wyszukiwarki rynkowej."

    return "\n".join(formatted_results)
