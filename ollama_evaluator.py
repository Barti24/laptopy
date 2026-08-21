import json
import logging
import re
from typing import Optional
import httpx
from models import Listing, EvaluationResult
from config import OLLAMA_URL, OLLAMA_MODEL, PROFIT_THRESHOLD_PLN, SHIPPING_COST_PLN

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Jesteś zaawansowanym rzeczoznawcą i ekspertem serwisu elektroniki oraz flippingu urządzeń w Polsce.
Twoim zadaniem jest dynamiczna ocena wartości rynkowej po naprawie oraz kosztów części zamiennych dla konkretnego egzemplarza elektroniki.

ZASADY DYNAMICZNEJ WYCENY CZĘŚCI I WARTOŚCI:
1. WYCENA CZĘŚCI (estimated_parts_cost_pln):
   - Dokładnie przeanalizuj model, generację i specyfikację z ogłoszenia.
   - Oszacuj realny rynkowy koszt zakupu wymaganych używanych lub zamiennych części w Polsce (dopasuj specyfikację: rodzaj RAM np. DDR3 vs DDR4 vs DDR5; typ dysku np. SATA SSD vs NVMe Gen3/Gen4; specyfikację matrycy; oryginalny zasilacz; chłodzenie; taśmy; obudowę).
   - NIE UŻYWAJ SZTYWNYCH LUB UŚREDNIONYCH KWOT. Oszaocuj koszty indywidualnie dla podanego modelu i wariantu sprzętu.

2. WARTOŚĆ RYNKOWA PO NAPRAWIE (estimated_resale_price_pln):
   - Oszaocuj aktualną, realną cenę sprzedaży sprawnego urządzenia tego konkretnego modelu na rynku wtórnym (OLX / Allegro / Vinted).

3. RYZYKO I CZARNA LISTA (BEZWZGLĘDNE ODRZUCENIE -> is_profitable = false):
   - Sprzęt z brakiem jednoznacznego opisu usterki, oznaczony jako "nietestowany", "stan nieznany", "stan nieokreślony" lub "na części bez podania usterki".
   - Zalane płynami / po zalaniu / korozja.
   - Wadliwe serie produkcyjne nieopłacalne w naprawie:
     * MacBook Pro 15" lub 17" z lat 2011-2012 (wadliwe układy GPU Radeon)
     * Konsole Xbox 360 z płyta Xenon lub Zephyr (błąd RROD / uszkodzenie GPU)
   - Wysokie ryzyko trwałego uszkodzenia płyty głównej, procesora lub bezpośredniego uszkodzenia rdzenia BGA / GPU die swap.

Zwróć odpowiedź WYŁĄCZNIE w formacie JSON zgodnym z poniższym schematem:
{
  "item_title": "<tytuł przedmiotu>",
  "category": "<kategoria sprzętu>",
  "detected_fault": "<Dokładny opis usterki>",
  "difficulty_level": "<Prosta / Średnia / Trudna>",
  "estimated_parts_cost_pln": <liczba całkowita - indywidualnie oszacowany koszt części w PLN dla danego modelu>,
  "estimated_resale_price_pln": <liczba całkowita - szacowana rynkowa cena sprzedaży sprawnego egzemplarza w PLN>,
  "net_profit_pln": <liczba całkowita - wzór: resale_price - (cena_zakupu + 30 + parts_cost)>,
  "roi_percentage": <liczba całkowita - zysk netto / całkowite wydatki * 100>,
  "is_profitable": <boolean - true tylko jeśli net_profit_pln >= 100 PLN i urządzenie NIE znajduje się na czarnej liście ani nie ma opisu 'stan nieznany/nietestowany/zalany'>,
  "recommendation_reason": "<Zwięzła, konkretna rekomendacja wyjaśniająca decyzję>"
}
"""

NO_FAULT_OR_UNKNOWN_PHRASES = [
    "brak usterki",
    "brak usterek",
    "sprzęt sprawny",
    "w pełni sprawny",
    "w pelni sprawny",
    "brak opisu usterki",
    "brak opisu uszkodzenia",
    "brak uszkodzeń",
    "brak uszkodzen",
    "sprawny",
    "stan idealny",
    "stan bardzo dobry",
    "nietestowany",
    "nietestowana",
    "nietestowane",
    "stan nieznany",
    "stan nieokreślony",
    "stan nieokreslony",
    "nieznany stan"
]

BLACK_LIST_PATTERNS = [
    r"macbook\s+pro\s+15.*2011",
    r"macbook\s+pro\s+17.*2011",
    r"macbook\s+pro\s+15.*2012",
    r"macbook\s+pro\s+17.*2012",
    r"macbook.*2011",
    r"macbook.*2012",
    r"xbox\s*360.*xenon",
    r"xbox\s*360.*zephyr",
    r"zalany",
    r"zalana",
    r"zalane",
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
    """Send listing details to Ollama API (Qwen 2.5) for dynamic repair evaluation."""
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

        # Resale price fallback logic supporting both field names
        resale_price_val = data.get("estimated_resale_price_pln") or data.get("estimated_market_value_working_pln")
        try:
            resale_price = int(resale_price_val if resale_price_val is not None else listing.price)
        except (ValueError, TypeError):
            resale_price = int(listing.price)

        total_expenses = listing.price + shipping_cost + parts_cost
        calculated_net_profit = int(resale_price - total_expenses)

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

        # Python enforcement of Strict Rejection rules:
        fault_lower = detected_fault.strip().lower()
        full_text = f"{listing.title} {listing.description} {detected_fault}".lower()

        # Rule 1: Reject if no clear fault / unknown state / untested / fully working
        if any(phrase in fault_lower for phrase in NO_FAULT_OR_UNKNOWN_PHRASES) or any(phrase in full_text for phrase in ["nietestowany", "stan nieznany", "nietestowane", "nietestowana"]):
            logger.info(f"Forcing is_profitable=False for {listing.id} due to no clear fault or untested/unknown state: '{detected_fault}'")
            is_profitable = False

        # Rule 2: Reject if item matches Blacklisted Series / Liquid Damage
        for pattern in BLACK_LIST_PATTERNS:
            if re.search(pattern, full_text):
                logger.info(f"Forcing is_profitable=False for {listing.id} due to blacklisted series/defect pattern '{pattern}'")
                is_profitable = False
                break

        recommendation_reason = str(data.get("recommendation_reason") or "Brak rekomendacji")

        return EvaluationResult(
            item_title=item_title,
            category=category,
            detected_fault=detected_fault,
            difficulty_level=difficulty_level,
            estimated_parts_cost_pln=parts_cost,
            estimated_resale_price_pln=resale_price,
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
            estimated_resale_price_pln=int(listing.price),
            net_profit_pln=0,
            roi_percentage=0,
            is_profitable=False,
            recommendation_reason=f"Błąd podczas analizy przez Ollama API: {e}"
        )
    finally:
        if should_close:
            client.close()
