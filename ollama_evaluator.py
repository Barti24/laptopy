import json
import logging
from typing import Optional
import httpx
from models import Listing, EvaluationResult
from config import OLLAMA_URL, OLLAMA_MODEL, PROFIT_THRESHOLD_PLN

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Jesteś ekspertem i rzeczoznawcą sprzętu komputerowego oraz elektroniki, specjalizującym się w flippingu (odsprzedaży z zyskiem) używanych laptopów w Polsce.
Twoim zadaniem jest oszacowanie realnej rynkowej wartości używanego laptopa na podstawie podanego tytułu ogłoszenia, podanej ceny oraz opisu.

Musisz zwrócić odpowiedź WYŁĄCZNIE w formacie JSON zgodnym z poniższym schematem:
{
  "estimated_market_value": <szacowana_wartość_rynkowa_w_PLN_jako_liczba>,
  "estimated_profit": <szacowany_zysk_w_PLN_czyli_wartość_rynkowa_minus_cena_ogłoszenia>,
  "reasoning": "<zwięzła_analiza_po_polsku_wyjaśniająca_oszacowanie_specyfikację_i_opłacalność>"
}

Zasady:
1. Przeanalizuj model, procesor, pamięć RAM, dysk, kartę graficzną oraz stan wizualny/techniczny opisany w ogłoszeniu.
2. Oszaocuj realną cenę, za jaką można sprzedać ten laptop na polskim rynku (Allegro/OLX).
3. Wylicz estimated_profit = estimated_market_value - cena_ogłoszenia.
4. Bądź ostrożny i konserwatywny w wycenie.
5. Zwróć wyłącznie prawidłowy obiekt JSON. Nie dodawaj żadnych tekstów wstępnych ani podsumowań poza obiektem JSON.
"""

def evaluate_listing_with_ollama(
    listing: Listing,
    client: Optional[httpx.Client] = None,
    ollama_url: str = OLLAMA_URL,
    model_name: str = OLLAMA_MODEL,
    profit_threshold: float = PROFIT_THRESHOLD_PLN
) -> EvaluationResult:
    """Send listing details to Ollama API and return EvaluationResult."""
    user_prompt = f"""Przeanalizuj poniższe ogłoszenie laptopa pod kątem opłacalności zakupu i flippingu:

Platforma: {listing.platform}
Tytuł ogłoszenia: {listing.title}
Cena w ogłoszeniu: {listing.price} {listing.currency}
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
        client = httpx.Client(timeout=60.0)
        should_close = True

    try:
        api_endpoint = f"{ollama_url.rstrip('/')}/api/chat"
        response = client.post(api_endpoint, json=payload)
        response.raise_for_status()

        response_data = response.json()
        content = response_data.get("message", {}).get("content", "")

        # Parse JSON from model response
        data = json.loads(content)

        estimated_market_value = float(data.get("estimated_market_value", 0.0))
        estimated_profit = float(data.get("estimated_profit", estimated_market_value - listing.price))
        reasoning = str(data.get("reasoning", "Brak uzasadnienia"))

        is_profitable = estimated_profit >= profit_threshold

        return EvaluationResult(
            estimated_market_value=estimated_market_value,
            estimated_profit=estimated_profit,
            reasoning=reasoning,
            is_profitable=is_profitable
        )

    except Exception as e:
        logger.error(f"Error evaluating listing {listing.id} via Ollama API: {e}")
        # Return fallback non-profitable valuation on error
        return EvaluationResult(
            estimated_market_value=listing.price,
            estimated_profit=0.0,
            reasoning=f"Błąd podczas wyceny przez Ollama API: {e}",
            is_profitable=False
        )
    finally:
        if should_close:
            client.close()
