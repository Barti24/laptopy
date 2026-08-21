import json
import logging
import re
from typing import Optional
import httpx
from models import Listing, EvaluationResult
from config import OLLAMA_URL, OLLAMA_MODEL, PROFIT_THRESHOLD_PLN, SHIPPING_COST_PLN

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Jesteś zaawansowanym rzeczoznawcą i ekspertem serwisu elektroniki oraz flippingu urządzeń w Polsce.
Twoim zadaniem jest ocena opłacalności zakupu i ewentualnej naprawy podanego przedmiotu.

ZASADY ANALIZY I SYSTEM PUNKTACJI (deal_score & verdict):
1. OCENA (deal_score): Przypisz punktację od 1 do 10:
   - 8-10: Wybitna okazja z wysoką marżą i niskim ryzykiem -> verdict: "OKAZJA"
   - 5-7: Ciekawa oferta warta obserwacji lub podjęcia negocjacji -> verdict: "OBSERWUJ"
   - 1-4: Nieopłacalny sprzęt, wysoka cena, duże ryzyko uszkodzenia lub brak opłacalności -> verdict: "ODRZUĆ"

2. WYCENA RYNKOWA I NAPRAWY:
   - estimated_market_value: Prognozowana realna cena sprzedaży sprawnego egzemplarza danego modelu na rynku wtórnym (Allegro/OLX/Vinted) w PLN.
   - estimated_repair_cost: Szacowany rynkowy koszt części zamiennych / naprawy w PLN (uwzględnij model, np. DDR3 vs DDR4, NVMe SSD, matrycę, napęd).
   - Aby oferta była opłacalna (deal_score >= 5), Zysk Netto = market_value - (cena_zakupu + 30 PLN wysyłka + repair_cost) powinien wynosić co najmniej 100 PLN.

3. KIEDY DAFOWAĆ VERDICT "ODRZUĆ" (deal_score 1-4):
   - Wymiana układów BGA/GPU die swap lub poważnie zalany sprzęt z korozją.
   - Wadliwe serie: MacBook Pro 15/17 z lat 2011-2012, Xbox 360 Xenon/Zephyr.

Zwróć odpowiedź WYŁĄCZNIE w formacie JSON zgodnym ze schematem:
{
  "item_title": "<tytuł przedmiotu>",
  "category": "<kategoria sprzętu>",
  "detected_fault": "<Krótki opis usterki lub stanu sprzętu>",
  "difficulty_level": "<Prosta / Średnia / Trudna / Brak>",
  "deal_score": <liczba całkowita od 1 do 10>,
  "verdict": "<OKAZJA | OBSERWUJ | ODRZUĆ>",
  "estimated_market_value": <liczba całkowita - szacowana cena rynkowa sprawnego sprzętu w PLN>,
  "estimated_repair_cost": <liczba całkowita - szacowany koszt części/naprawy w PLN>,
  "reasoning": "<Zwięzłe uzasadnienie decyzji w 1-2 zdaniach po polsku>"
}
"""

BLACK_LIST_PATTERNS = [
    r"macbook\s+pro\s+15.*2011",
    r"macbook\s+pro\s+17.*2011",
    r"macbook\s+pro\s+15.*2012",
    r"macbook\s+pro\s+17.*2012",
    r"macbook.*2011",
    r"macbook.*2012",
    r"xbox\s*360.*xenon",
    r"xbox\s*360.*zephyr",
    r"po zalaniu",
    r"cieczą",
    r"płynem"
]

def evaluate_listing_with_ollama(
    listing: Listing,
    client: Optional[httpx.Client] = None,
    ollama_url: str = OLLAMA_URL,
    model_name: str = OLLAMA_MODEL,
    profit_threshold: float = PROFIT_THRESHOLD_PLN,
    shipping_cost: float = SHIPPING_COST_PLN
) -> EvaluationResult:
    """Send listing details to Ollama API (Qwen 2.5) for scoring (deal_score 1-10 & verdict) and repair evaluation."""
    user_prompt = f"""Przeanalizuj poniższe ogłoszenie pod kątem opłacalności zakupu, naprawy i flippingu:

Kategoria: {listing.category}
Platforma: {listing.platform}
Tytuł ogłoszenia: {listing.title}
Cena zakupu: {listing.price} {listing.currency}
Opis:
{listing.description}
"""

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        "format": "json",
        "stream": False
    }

    should_close = False
    if client is None:
        client = httpx.Client(timeout=None)
        should_close = True

    try:
        api_endpoint = f"{ollama_url.rstrip('/')}/api/chat"
        response = client.post(api_endpoint, json=payload, timeout=None)
        response.raise_for_status()

        response_data = response.json()
        content = response_data.get("message", {}).get("content", "").strip()

        if content.startswith("```"):
            content = re.sub(r'^```(?:json)?\n|\n```$', '', content, flags=re.MULTILINE).strip()

        data = json.loads(content)

        item_title = str(data.get("item_title") or listing.title)
        category = str(data.get("category") or listing.category)
        detected_fault = str(data.get("detected_fault") or "Brak opisu usterki")
        difficulty_level = str(data.get("difficulty_level") or "Średnia")

        try:
            repair_cost = int(data.get("estimated_repair_cost", data.get("estimated_parts_cost_pln", 0)))
        except (ValueError, TypeError):
            repair_cost = 0

        market_val_data = data.get("estimated_market_value") or data.get("estimated_resale_price_pln") or data.get("estimated_market_value_working_pln")
        try:
            market_val = int(market_val_data if market_val_data is not None else listing.price)
        except (ValueError, TypeError):
            market_val = int(listing.price)

        total_expenses = listing.price + shipping_cost + repair_cost
        calculated_net_profit = int(market_val - total_expenses)

        if total_expenses > 0:
            roi_percentage = int((calculated_net_profit / total_expenses) * 100)
        else:
            roi_percentage = 0

        try:
            raw_score = int(data.get("deal_score", 1))
            deal_score = max(1, min(10, raw_score))
        except (ValueError, TypeError):
            deal_score = 1

        verdict_str = str(data.get("verdict", "")).strip().upper()
        if "OKAZJA" in verdict_str:
            verdict = "OKAZJA"
        elif "OBSERWUJ" in verdict_str:
            verdict = "OBSERWUJ"
        elif "ODRZUĆ" in verdict_str or "ODRZUC" in verdict_str:
            verdict = "ODRZUĆ"
        else:
            if deal_score >= 8:
                verdict = "OKAZJA"
            elif deal_score >= 5:
                verdict = "OBSERWUJ"
            else:
                verdict = "ODRZUĆ"

        is_profitable = (deal_score >= 5) and (verdict in ["OKAZJA", "OBSERWUJ"])

        # Python enforcement of Blacklisted Hardware Series / Liquid damage
        full_text = f"{listing.title} {listing.description} {detected_fault}".lower()
        for pattern in BLACK_LIST_PATTERNS:
            if re.search(pattern, full_text):
                logger.info(f"Overriding verdict for {listing.id} to ODRZUĆ due to blacklisted defect pattern '{pattern}'")
                deal_score = min(deal_score, 3)
                verdict = "ODRZUĆ"
                is_profitable = False
                break

        reasoning = str(data.get("reasoning") or data.get("recommendation_reason") or "Brak uzasadnienia")

        return EvaluationResult(
            item_title=item_title,
            category=category,
            detected_fault=detected_fault,
            difficulty_level=difficulty_level,
            deal_score=deal_score,
            verdict=verdict,
            estimated_market_value=market_val,
            estimated_repair_cost=repair_cost,
            net_profit_pln=calculated_net_profit,
            roi_percentage=roi_percentage,
            is_profitable=is_profitable,
            reasoning=reasoning
        )

    except Exception as e:
        logger.error(f"Error evaluating listing {listing.id} via Ollama API: {e}")
        return EvaluationResult(
            item_title=listing.title,
            category=listing.category,
            detected_fault="Błąd analizy API",
            difficulty_level="Trudna",
            deal_score=1,
            verdict="ODRZUĆ",
            estimated_market_value=int(listing.price),
            estimated_repair_cost=0,
            net_profit_pln=0,
            roi_percentage=0,
            is_profitable=False,
            reasoning=f"Błąd podczas analizy przez Ollama API: {e}"
        )
    finally:
        if should_close:
            client.close()
