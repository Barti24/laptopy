import argparse
import json
import logging
import os
import sys
import time
from typing import Set, List
import httpx

from config import (
    FETCH_INTERVAL_SECONDS,
    SEEN_CACHE_FILE,
    PROFIT_THRESHOLD_PLN,
    OLLAMA_MODEL,
    DEFAULT_HEADERS,
    CATEGORIES
)
from models import Listing, EvaluationResult
from scrapers.olx import fetch_olx_listings
from scrapers.vinted import fetch_vinted_listings
from ollama_evaluator import evaluate_listing_with_ollama
from notifier import notify_profitable_listing

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("main")

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

def run_monitoring_cycle(
    seen_ids: Set[str],
    dry_run: bool = False,
    client: httpx.Client = None
) -> List[Listing]:
    """Execute a single cycle of fetching across categories, evaluating repairs, and notifying."""
    logger.info("Starting multi-category electronics monitoring cycle...")

    all_listings: List[Listing] = []

    for cat_name, cat_config in CATEGORIES.items():
        logger.info(f"Scanning category: {cat_name}...")
        olx_items = fetch_olx_listings(client=client, url=cat_config["olx_url"], category=cat_name)
        vinted_items = fetch_vinted_listings(client=client, search_text=cat_config["vinted_search"], category=cat_name)
        logger.info(f"[{cat_name}] Fetched {len(olx_items)} from OLX, {len(vinted_items)} from Vinted.")
        all_listings.extend(olx_items + vinted_items)

    new_listings = [item for item in all_listings if item.id not in seen_ids]
    logger.info(f"Found {len(new_listings)} total new listings to evaluate across all categories.")

    processed_listings = []

    for listing in new_listings:
        seen_ids.add(listing.id)
        logger.info(f"Evaluating [{listing.category} - {listing.platform}]: {listing.title} ({listing.price} {listing.currency})")

        if dry_run:
            logger.info(f"[DRY-RUN] Mocking evaluation for {listing.id}")
            evaluation = EvaluationResult(
                item_title=listing.title,
                category=listing.category,
                detected_fault="[DRY-RUN Mock] Brak zasilania / usterka kosmetyczna",
                difficulty_level="Prosta",
                estimated_parts_cost_pln=30,
                estimated_market_value_working_pln=int(listing.price + 250),
                net_profit_pln=205,
                roi_percentage=120,
                is_profitable=True,
                recommendation_reason="[DRY-RUN Mock] Łatwa wymiana bezpiecznika/zasilacza, wysoki zysk netto."
            )
        else:
            evaluation = evaluate_listing_with_ollama(listing, client=client)

        logger.info(
            f"Result for {listing.id}: Net Profit={evaluation.net_profit_pln} PLN, ROI={evaluation.roi_percentage}%, "
            f"Profitable={evaluation.is_profitable}, Fault='{evaluation.detected_fault}'"
        )

        if evaluation.is_profitable:
            logger.info(f"🔥 HIGH PROFIT REPAIR CANDIDATE FOUND ({evaluation.net_profit_pln} PLN >= {PROFIT_THRESHOLD_PLN} PLN)! Dispatching notifications...")
            if not dry_run:
                notify_profitable_listing(listing, evaluation, client=client)
            else:
                logger.info(f"[DRY-RUN] Would send notification for {listing.title}")

        processed_listings.append(listing)

    save_seen_ids(seen_ids)
    logger.info("Monitoring cycle completed.")
    return processed_listings

def main():
    parser = argparse.ArgumentParser(description="Multi-category Electronics Repair & Flipping Monitor")
    parser.add_argument("--once", action="store_true", help="Run a single check cycle and exit")
    parser.add_argument("--dry-run", action="store_true", help="Run without calling Ollama API or sending webhooks")
    parser.add_argument("--interval", type=int, default=FETCH_INTERVAL_SECONDS, help="Fetch interval in seconds")
    args = parser.parse_args()

    logger.info(f"Starting Electronics Repair Monitor (Ollama model: {OLLAMA_MODEL}, Profit threshold: {PROFIT_THRESHOLD_PLN} PLN)")

    seen_ids = load_seen_ids()
    logger.info(f"Loaded {len(seen_ids)} previously seen listing IDs.")

    with httpx.Client(headers=DEFAULT_HEADERS, timeout=30.0, follow_redirects=True) as client:
        if args.once:
            run_monitoring_cycle(seen_ids, dry_run=args.dry_run, client=client)
        else:
            logger.info(f"Running continuously with {args.interval} seconds interval...")
            while True:
                try:
                    run_monitoring_cycle(seen_ids, dry_run=args.dry_run, client=client)
                except Exception as e:
                    logger.error(f"Unexpected error in monitoring cycle: {e}")
                time.sleep(args.interval)

if __name__ == "__main__":
    main()
