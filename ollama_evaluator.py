import json
import logging
import re
from typing import Optional
import httpx
from models import Listing, EvaluationResult
from config import OLLAMA_URL, OLLAMA_MODEL, PROFIT_THRESHOLD_PLN, SHIPPING_COST_PLN

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Jesteś ekspertem i rzeczoznawcą serwisu elektroniki oraz flippingu urządzeń w Polsce.
Twoim zadaniem jest ocena opłacalności zakupu i naprawy sprzętu elektronicznego na podstawie podanych danych ogłoszenia.

Przeanalizuj tytuł, kategoryzację, cenę zakupu oraz opis ogłoszenia i zwróć odpowiedź WYŁĄCZNIE w formacie JSON zgodnym z poniższym schematem:

{
  "item_title": "<tytuł przedmiotu>",
  "category": "<kategoria sprzętu>",
  "detected_fault": "<Krótki opis wykrytej usterki na podstawie opisu ogłoszenia>",
  "difficulty_level": "<Prosta / Średnia / Trudna>",
  "estimated_parts_cost_pln": <liczba całkowita - szacowany koszt części w PLN, np. pasta, dysk, zasilacz, HDMI, wentylator>,
  "estimated_market_value_working_pln": <liczba całkowita - realna wartość rynkowa po naprawie na OLX/Allegro w PLN>,
  "net_profit_pln": <liczba całkowita - wzór: market_value - (cena_zakupu + 15 + estimated_parts_cost)>,
  "roi_percentage": <liczba całkowita - zysk netto / całkowite wydatki * 100>,
  "is_profitable": <boolean - true jeśli net_profit_pln >= 100 PLN i brak ryzyka uszkodzenia płyty głównej/CPU/GPU chipa, w przeciwnym razie false>,
  "recommendation_reason": "<Jedno zdanie wyjaśniające dlaczego warto lub nie warto brać>"
}

Zasady oceny opłacalności:
1. Koszt wysyłki to zawsze 15 PLN. Całkowite wydatki = Cena Zakupu + 15 PLN + Szacowany Koszt Części.
2. Wzór na net_profit_pln = estimated_market_value_working_pln - (Cena Zakupu + 15 + estimated_parts_cost_pln).
3. Wzór na roi_percentage = (net_profit_pln / Całkowite Wydatki) * 100.
4. is_profitable musi wynosić `true` tylko jeśli:
   - net_profit_pln >= 100 PLN
   - ORAZ BRAK wysokiego ryzyka trwałego uszkodzenia płyty głównej, procesora lub układu graficznego (BGA/CPU/GPU die swap), którego naprawa jest nieopłacalna.
5. Zwróć wyłącznie prawidłowy, czysty obiekt JSON. Nie dodawaj żadnych tekstów wstępnych ani podsumowań poza obiektem JSON.
"""

def evaluate_listing_with_ollama(
    listing: Listing,
    client: Optional[httpx.Client] = None,
    ollama_url: str = OLLAMA_URL,
    model_name: str = OLLAMA_MODEL,
    profit_threshold: float = PROFIT_THRESHOLD_PLN,
    shipping_cost: float = SHIPPING_COST_PLN
) -> EvaluationResult:
    """Send listing details to Ollama API (Qwen 2.5) for repair evaluation with no timeout (timeout=None)."""
    user_prompt = f"""Przeanalizuj poniższe ogłoszenie pod kątem opłacalności naprawy i odsprzedaży:

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
            parts_cost = int(data.get("estimated_parts_cost_pln", 0))
        except (ValueError, TypeError):
            parts_cost = 0

        try:
            market_val_working = int(data.get("estimated_market_value_working_pln", int(listing.price)))
        except (ValueError, TypeError):
            market_val_working = int(listing.price)

        total_expenses = listing.price + shipping_cost + parts_cost
        calculated_net_profit = int(market_val_working - total_expenses)

        if "net_profit_pln" in data and isinstance(data["net_profit_pln"], (int, float)):
            net_profit = int(data["net_profit_pln"])
        else:
            net_profit = calculated_net_profit

        if total_expenses > 0:
            roi_percentage = int((net_profit / total_expenses) * 100)
        else:
            roi_percentage = 0

        is_profitable_llm = bool(data.get("is_profitable", False))
        is_profitable = is_profitable_llm and (net_profit >= profit_threshold)

        recommendation_reason = str(data.get("recommendation_reason") or "Brak rekomendacji")

        return EvaluationResult(
            item_title=item_title,
            category=category,
            detected_fault=detected_fault,
            difficulty_level=difficulty_level,
            estimated_parts_cost_pln=parts_cost,
            estimated_market_value_working_pln=market_val_working,
            net_profit_pln=net_profit,
            roi_percentage=roi_percentage,
            is_profitable=is_profitable,
            recommendation_reason=recommendation_reason
        )

    except Exception as e:
        logger.error(f"Error evaluating listing {listing.id} via Ollama API: {e}")
        return EvaluationResult(
            item_title=listing.title,
            category=listing.category,
            detected_fault="Błąd analizy API",
            difficulty_level="Trudna",
            estimated_parts_cost_pln=0,
            estimated_market_value_working_pln=int(listing.price),
            net_profit_pln=0,
            roi_percentage=0,
            is_profitable=False,
            recommendation_reason=f"Błąd podczas analizy przez Ollama API: {e}"
        )
    finally:
        if should_close:
            client.close()
