import argparse
import json
import logging
import os
import sys
import time
from typing import Set, List
import httpx
from curl_cffi import requests as curl_requests

from config import (
    FETCH_INTERVAL_SECONDS,
    SEEN_CACHE_FILE,
    PROFIT_THRESHOLD_PLN,
    OLLAMA_MODEL,
    CATEGORIES,
    FAULT_KEYWORDS
)
from models import Listing, EvaluationResult
from scrapers.vinted import fetch_vinted_listings_deep
from ollama_evaluator import evaluate_listing_with_ollama
from notifier import notify_profitable_listing

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("main")

MAX_PAGES_PER_CATEGORY = 5

def load_seen_ids(cache_file: str = SEEN_CACHE_FILE) -> Set[str]:
    """Load seen listing IDs from persistent cache file."""
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return set(data)
        except Exception as e:
            logger.warning(f"Error reading seen IDs cache file {cache_file}: {e}")
    return set()

def save_seen_ids(seen_ids: Set[str], cache_file: str = SEEN_CACHE_FILE) -> None:
    """Save seen listing IDs to persistent cache file."""
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(list(seen_ids), f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving seen IDs to cache file {cache_file}: {e}")

def passes_pre_filter(listing: Listing, max_price: float) -> bool:
    """Check if listing price is below category limit and contains at least one fault keyword."""
    if listing.price > max_price:
        logger.info(f"Skipping [{listing.id}] - Price {listing.price} PLN exceeds category max limit {max_price} PLN.")
        return False

    text_to_check = f"{listing.title} {listing.description}".lower()
    has_fault_keyword = any(kw.lower() in text_to_check for kw in FAULT_KEYWORDS)

    if not has_fault_keyword:
        logger.info(f"Skipping [{listing.id}] - Title/Description does not contain any fault/damage keyword.")
        return False

    return True

def run_monitoring_cycle(
    seen_ids: Set[str],
    dry_run: bool = False,
    scraper_session: curl_requests.Session = None,
    http_client: httpx.Client = None,
    max_pages: int = MAX_PAGES_PER_CATEGORY
) -> List[Listing]:
    """Execute a single cycle of deep-scan fetching across categories (Vinted), pre-filtering, evaluating repairs, and notifying."""
    logger.info("Starting multi-category electronics deep-scan monitoring cycle (Vinted)...")

    new_candidates_to_eval: List[Listing] = []

    for cat_name, cat_config in CATEGORIES.items():
        logger.info(f"Scanning category on Vinted: {cat_name} (up to {max_pages} pages)...")
        scraped_items = fetch_vinted_listings_deep(
            session=scraper_session,
            search_text=cat_config["vinted_search"],
            category=cat_name,
            seen_ids=seen_ids,
            max_pages=max_pages
        )

        max_price = cat_config.get("max_price", 999999.0)

        cat_new_candidates = 0
        for item in scraped_items:
            if item.id in seen_ids:
                continue

            # Ensure every examined item is recorded in seen_ids immediately
            seen_ids.add(item.id)

            if passes_pre_filter(item, max_price=max_price):
                new_candidates_to_eval.append(item)
                cat_new_candidates += 1

        logger.info(f"[{cat_name}] {len(scraped_items)} items retrieved, {cat_new_candidates} passed pre-filter for LLM evaluation.")

    # Immediately persist updated seen_ids
    save_seen_ids(seen_ids)

    logger.info(f"Found {len(new_candidates_to_eval)} total pre-filtered new listings to evaluate with Ollama AI.")

    processed_listings = []

    for listing in new_candidates_to_eval:
        logger.info(f"Evaluating [{listing.category} - {listing.platform}]: {listing.title} ({listing.price} {listing.currency})")

        if dry_run:
            logger.info(f"[DRY-RUN] Mocking evaluation for {listing.id}")
            evaluation = EvaluationResult(
                item_title=listing.title,
                category=listing.category,
                detected_fault="[DRY-RUN Mock] Brak zasilania / usterka kosmetyczna",
                difficulty_level="Prosta",
                estimated_parts_cost_pln=30,
                estimated_resale_price_pln=int(listing.price + 250),
                net_profit_pln=190,
                roi_percentage=110,
                is_profitable=True,
                recommendation_reason="[DRY-RUN Mock] Łatwa wymiana bezpiecznika/zasilacza, wysoki zysk netto."
            )
        else:
            evaluation = evaluate_listing_with_ollama(listing, client=http_client)

        logger.info(
            f"Result for {listing.id}: Net Profit={evaluation.net_profit_pln} PLN, ROI={evaluation.roi_percentage}%, "
            f"Profitable={evaluation.is_profitable}, Fault='{evaluation.detected_fault}'"
        )

        if evaluation.is_profitable:
            logger.info(f"🔥 HIGH PROFIT REPAIR CANDIDATE FOUND ({evaluation.net_profit_pln} PLN >= {PROFIT_THRESHOLD_PLN} PLN)! Dispatching notifications...")
            if not dry_run:
                notify_profitable_listing(listing, evaluation, client=http_client)
            else:
                logger.info(f"[DRY-RUN] Would send notification for {listing.title}")

        processed_listings.append(listing)

    # Save final seen_ids state after evaluation loop
    save_seen_ids(seen_ids)
    logger.info("Monitoring cycle completed.")
    return processed_listings

def main():
    parser = argparse.ArgumentParser(description="Multi-category Electronics Repair & Flipping Monitor (Vinted Deep Scan)")
    parser.add_argument("--once", action="store_true", help="Run a single check cycle and exit")
    parser.add_argument("--dry-run", action="store_true", help="Run without calling Ollama API or sending webhooks")
    parser.add_argument("--interval", type=int, default=FETCH_INTERVAL_SECONDS, help="Fetch interval in seconds")
    parser.add_argument("--max-pages", type=int, default=MAX_PAGES_PER_CATEGORY, help="Max history pages per category per cycle")
    args = parser.parse_args()

    logger.info(f"Starting Electronics Repair Monitor (Ollama model: {OLLAMA_MODEL}, Profit threshold: {PROFIT_THRESHOLD_PLN} PLN)")

    seen_ids = load_seen_ids()
    logger.info(f"Loaded {len(seen_ids)} previously seen listing IDs.")

    with curl_requests.Session(impersonate="chrome120") as scraper_session, httpx.Client(timeout=None) as http_client:
        if args.once:
            run_monitoring_cycle(
                seen_ids,
                dry_run=args.dry_run,
                scraper_session=scraper_session,
                http_client=http_client,
                max_pages=args.max_pages
            )
        else:
            logger.info(f"Running continuously with {args.interval} seconds interval...")
            while True:
                try:
                    run_monitoring_cycle(
                        seen_ids,
                        dry_run=args.dry_run,
                        scraper_session=scraper_session,
                        http_client=http_client,
                        max_pages=args.max_pages
                    )
                except Exception as e:
                    logger.error(f"Unexpected error in monitoring cycle: {e}")
                time.sleep(args.interval)

if __name__ == "__main__":
    main()
