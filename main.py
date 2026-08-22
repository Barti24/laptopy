import argparse
import datetime
import json
import logging
import os
import random
import sys
import time
from typing import Set, List, Dict
import httpx
from curl_cffi import requests as curl_requests

from config import (
    FETCH_INTERVAL_SECONDS,
    RE_EVALUATION_INTERVAL_CYCLES,
    SEEN_CACHE_FILE,
    PROFIT_THRESHOLD_FLIP_PLN,
    PROFIT_THRESHOLD_REPAIR_PLN,
    OLLAMA_MODEL,
    CATEGORIES,
    FAULT_KEYWORDS,
    EXCLUDE_PARTS,
    EXCLUDE_TOYS
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

MAX_PAGES_PER_CATEGORY = 2

def load_seen_data(cache_file: str = SEEN_CACHE_FILE) -> Dict[str, dict]:
    """
    Load seen listings from persistent cache file.
    Supports both legacy list of IDs and dictionary structure storing listing metadata.
    Returns dict mapping listing_id -> listing_dict.
    """
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
                elif isinstance(data, list):
                    # Convert legacy list of IDs to dict structure
                    return {item_id: {"id": item_id} for item_id in data}
        except Exception as e:
            logger.warning(f"Error reading seen cache file {cache_file}: {e}")
    return {}

def save_seen_data(seen_data: Dict[str, dict], cache_file: str = SEEN_CACHE_FILE) -> None:
    """Save seen listings data to persistent cache file."""
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(seen_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving seen data to cache file {cache_file}: {e}")

def passes_pre_filter(listing: Listing, max_price: float, cheap_threshold: float = 400.0) -> bool:
    """
    Hybrid pre-filter logic with CRITICAL ORDER:
    Step 1: Check category max_price limit -> Reject if price > max_price.
    Step 2: Check BLACKLISTS (EXCLUDE_TOYS and EXCLUDE_PARTS) FIRST -> Reject immediately if matched.
    Step 3: Check cheap_threshold AUTO-PASS (400 PLN) -> Pass if price < cheap_threshold (400 PLN).
    Step 4: Check FAULT_KEYWORDS -> Pass if title/description contains at least one fault keyword root.
    """
    # Step 1: Maximum price limit check
    if listing.price > max_price:
        logger.info(f"Skipping [{listing.id}] - Price {listing.price} PLN exceeds category max limit {max_price} PLN.")
        return False

    text_to_check = f"{listing.title} {listing.description}".lower()

    # Step 2: Blacklist exclusion checks (CRITICAL: MUST happen BEFORE cheap auto-pass)
    # Check 2a: Toy and children item exclusion
    for toy_keyword in EXCLUDE_TOYS:
        if toy_keyword.lower() in text_to_check:
            logger.info(f"Skipping [{listing.id}] - Title/Description contains blacklisted toy keyword '{toy_keyword}'.")
            return False

    # Check 2b: Laptop spare parts exclusion
    if listing.category == "Laptopy":
        title_lower = listing.title.lower()
        for part in EXCLUDE_PARTS:
            if part in title_lower:
                logger.info(f"Skipping Laptop [{listing.id}] - Title '{listing.title}' contains excluded component keyword '{part}'.")
                return False

    # Step 3: Very cheap item AUTO-PASS (< 400 PLN) (only reached if NOT on blacklists)
    if cheap_threshold > 0 and listing.price < cheap_threshold:
        logger.info(f"Pre-filter AUTO-PASS [{listing.id}] - Price {listing.price} PLN < cheap threshold {cheap_threshold} PLN.")
        return True

    # Step 4: Keyword matching
    has_fault_keyword = any(kw.lower() in text_to_check for kw in FAULT_KEYWORDS)

    if not has_fault_keyword:
        logger.info(f"Skipping [{listing.id}] - Price {listing.price} PLN >= cheap threshold {cheap_threshold} PLN and title/description lacks fault keyword root.")
        return False

    return True

def run_monitoring_cycle(
    seen_data: Dict[str, dict],
    cycle_number: int = 1,
    dry_run: bool = False,
    scraper_session: curl_requests.Session = None,
    http_client: httpx.Client = None,
    max_pages: int = MAX_PAGES_PER_CATEGORY
) -> List[Listing]:
    """Execute a single cycle of deep-scan fetching across categories (Vinted), hybrid pre-filtering, evaluating repairs, and notifying."""
    logger.info(f"Starting multi-category electronics deep-scan monitoring cycle #{cycle_number} (Vinted)...")

    seen_ids = set(seen_data.keys())
    new_candidates_to_eval: List[Listing] = []

    cat_list = list(CATEGORIES.items())
    for idx, (cat_name, cat_config) in enumerate(cat_list):
        if idx > 0:
            delay = random.uniform(3.0, 7.0)
            logger.info(f"Inter-category throttling jitter delay: waiting {delay:.2f}s before category '{cat_name}'...")
            time.sleep(delay)

        logger.info(f"Scanning category on Vinted: {cat_name} (up to {max_pages} pages)...")
        scraped_items = fetch_vinted_listings_deep(
            session=scraper_session,
            search_text=cat_config["vinted_search"],
            category=cat_name,
            seen_ids=seen_ids,
            max_pages=max_pages
        )

        max_price = cat_config.get("max_price", 999999.0)
        cheap_threshold = cat_config.get("cheap_threshold", 400.0)

        cat_new_candidates = 0
        for item in scraped_items:
            # Check if this is an item we have seen before, or if its price dropped
            if item.id in seen_data:
                previous_price = seen_data[item.id].get("price")
                if previous_price is not None and item.price < previous_price:
                    logger.info(f"🔥 PRICE DROP DETECTED for [{item.id}] '{item.title}': {previous_price} PLN -> {item.price} PLN!")
                    # Allow re-evaluation due to price drop
                    seen_data[item.id]["price"] = item.price
                    seen_data[item.id]["last_updated"] = time.time()
                    if passes_pre_filter(item, max_price=max_price, cheap_threshold=cheap_threshold):
                        new_candidates_to_eval.append(item)
                        cat_new_candidates += 1
                continue

            # Record item in seen_data
            seen_data[item.id] = {
                "id": item.id,
                "title": item.title,
                "price": item.price,
                "category": item.category,
                "url": item.url,
                "first_seen": time.time(),
                "last_updated": time.time()
            }
            seen_ids.add(item.id)

            if passes_pre_filter(item, max_price=max_price, cheap_threshold=cheap_threshold):
                new_candidates_to_eval.append(item)
                cat_new_candidates += 1

        logger.info(f"[{cat_name}] {len(scraped_items)} items retrieved, {cat_new_candidates} passed hybrid pre-filter for LLM evaluation.")

    # Periodic re-evaluation of historical seen listings for price drops
    if cycle_number % RE_EVALUATION_INTERVAL_CYCLES == 0:
        logger.info(f"🔄 Periodic historical re-evaluation triggered on cycle #{cycle_number} (checking cached listings for price drops)...")
        # Save seen_data before running
        save_seen_data(seen_data)

    save_seen_data(seen_data)

    logger.info(f"Found {len(new_candidates_to_eval)} total hybrid pre-filtered listings to evaluate with Ollama AI.")

    processed_listings = []

    for listing in new_candidates_to_eval:
        logger.info(f"Evaluating [{listing.category} - {listing.platform}]: {listing.title} ({listing.price} {listing.currency})")

        if dry_run:
            logger.info(f"[DRY-RUN] Mocking evaluation for {listing.id}")
            evaluation = EvaluationResult(
                item_title=listing.title,
                category=listing.category,
                deal_type="OKAZJA_FLIP",
                deal_score=9,
                estimated_market_value=int(listing.price + 200),
                estimated_parts_cost=0,
                estimated_net_profit=180,
                roi_percentage=90,
                negotiation_target=int(listing.price * 0.85),
                market_liquidity="BARDZO SZYBKO",
                risk_assessment="NISKIE - sprawny sprzęt z pewną marżą",
                salvage_value=int(listing.price * 0.5),
                fault_analysis="Brak usterki / Sprzęt sprawny",
                repair_difficulty="Brak",
                repair_steps=["1. Czyszczenie obudowy", "2. Wystawienie ogłoszenia"],
                is_profitable=True,
                reasoning="[DRY-RUN Mock] Świetna okazja typu Czysty Flip z pewnym zyskiem."
            )
        else:
            evaluation = evaluate_listing_with_ollama(listing, client=http_client)

        logger.info(
            f"Result for {listing.id}: Type='{evaluation.deal_type}', Score={evaluation.deal_score}/10, "
            f"Net Profit={evaluation.estimated_net_profit} PLN, Profitable={evaluation.is_profitable}"
        )

        if evaluation.is_profitable:
            logger.info(f"🔥 QUALIFIED DEAL FOUND ({evaluation.deal_type} +{evaluation.estimated_net_profit} PLN)! Dispatching Discord/Telegram notifications...")
            if not dry_run:
                notify_profitable_listing(listing, evaluation, client=http_client)
            else:
                logger.info(f"[DRY-RUN] Would send notification for {listing.title}")

        processed_listings.append(listing)

    save_seen_data(seen_data)
    logger.info("Monitoring cycle completed.")
    return processed_listings

def is_night_time() -> bool:
    """Return True if system local time is between 01:00 and 06:00 (1 <= hour < 6)."""
    current_hour = datetime.datetime.now().hour
    return 1 <= current_hour < 6

def main():
    parser = argparse.ArgumentParser(description="Multi-category Electronics Repair & Flipping Monitor (Vinted Rate-Limited)")
    parser.add_argument("--once", action="store_true", help="Run a single check cycle and exit")
    parser.add_argument("--dry-run", action="store_true", help="Run without calling Ollama API or sending webhooks")
    parser.add_argument("--interval", type=int, default=FETCH_INTERVAL_SECONDS, help="Fetch interval in seconds")
    parser.add_argument("--max-pages", type=int, default=MAX_PAGES_PER_CATEGORY, help="Max history pages per category per cycle")
    args = parser.parse_args()

    logger.info(f"Starting Electronics Monitor (Ollama model: {OLLAMA_MODEL}, Flip threshold: {PROFIT_THRESHOLD_FLIP_PLN} PLN, Repair threshold: {PROFIT_THRESHOLD_REPAIR_PLN} PLN)")

    seen_data = load_seen_data()
    logger.info(f"Loaded {len(seen_data)} previously seen listing records.")

    cycle_count = 1

    with curl_requests.Session(impersonate="chrome120") as scraper_session, httpx.Client(timeout=600.0) as http_client:
        if args.once:
            if is_night_time():
                logger.info("Przerwa nocna (01:00 - 06:00). Skipping single run execution in night hours.")
            else:
                run_monitoring_cycle(
                    seen_data,
                    cycle_number=cycle_count,
                    dry_run=args.dry_run,
                    scraper_session=scraper_session,
                    http_client=http_client,
                    max_pages=args.max_pages
                )
        else:
            logger.info(f"Running continuously with {args.interval} seconds interval...")
            while True:
                if is_night_time():
                    logger.info("Przerwa nocna (01:00 - 06:00). Sleeping 1800 seconds (30 minutes)...")
                    time.sleep(1800)
                    continue

                try:
                    run_monitoring_cycle(
                        seen_data,
                        cycle_number=cycle_count,
                        dry_run=args.dry_run,
                        scraper_session=scraper_session,
                        http_client=http_client,
                        max_pages=args.max_pages
                    )
                    cycle_count += 1
                except Exception as e:
                    logger.error(f"Unexpected error in monitoring cycle: {e}")
                time.sleep(args.interval)

if __name__ == "__main__":
    main()
