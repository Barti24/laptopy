import json
import logging
import re
from typing import Optional, List
import httpx
from models import Listing, EvaluationResult
from config import (
    OLLAMA_URL,
    OLLAMA_MODEL,
    PROFIT_THRESHOLD_FLIP_PLN,
    PROFIT_THRESHOLD_REPAIR_PLN,
    SHIPPING_COST_PLN
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Jesteś zaawansowanym rzeczoznawcą i ekspertem serwisu elektroniki oraz flippingu urządzeń w Polsce.
Twoim zadaniem jest ocena opłacalności zakupu dla DWÓCH typów okazji: "OKAZJA_FLIP" (sprawny/nowy sprzęt tanio) oraz "OKAZJA_NAPRAWA" (uszkodzenie/wada z potencjałem zysku po naprawie).

ZASADY ANALIZY I KLASYFIKACJI (deal_type):
1. "OKAZJA_FLIP" (Czysty Flip):
   - Sprzęt jest w 100% sprawny lub w stanie idealnym, a niska cena zakupu daje wyrazisty margines zysku bez konieczności naprawy.
   - Koszt części / naprawy = 0 PLN.
   - Zysk netto = (cena rynkowa - cena zakupu - 20 PLN wysyłka).

2. "OKAZJA_NAPRAWA" (Sprzęt Do Naprawy):
   - Sprzęt posiada opisaną usterkę, wadę kosmetyczną lub brak części, ale naprawa jest opłacalna.
   - Koszt części / naprawy (estimated_parts_cost) musi być oszacowany dynamicznie dla podanego modelu (np. matryca, bateria, dysk SSD, laser, zasilacz).
   - Zysk netto = (cena rynkowa po naprawie - cena zakupu - koszt części - 20 PLN wysyłka).

3. "BRAK_ZYSKU" (Odrzuć):
   - Sprzęt nieopłacalny, za droga oferta, lub występują krytyczne wady BGA/zalanie/czarna lista.

STRATEGIA I CZARNA LISTA:
- negotiation_target: Sugerowana kwota pierwszej oferty negocjacyjnej na Vinted w PLN (o ok. 10-20% niższa od ceny ogłoszenia).
- market_liquidity: Ocena czasu odsprzedaży ("BARDZO SZYBKO", "ŚREDNIO", "NISKA PŁYNNOŚĆ").
- risk_assessment: Poziom ryzyka ("NISKIE", "ŚREDNIE", "WYSOKIE") z krótkim uzasadnieniem.
- salvage_value: Przewidywana wartość samych sprawnych części w PLN (Plan B / dawca, jeśli naprawa lub sprzedaż zawiedzie).

Zwróć odpowiedź WYŁĄCZNIE w formacie JSON zgodnym ze schematem:
{
  "item_title": "<tytuł przedmiotu>",
  "category": "<kategoria sprzętu>",
  "deal_type": "<OKAZJA_FLIP | OKAZJA_NAPRAWA | BRAK_ZYSKU>",
  "deal_score": <liczba całkowita od 1 do 10>,
  "estimated_market_value": <liczba całkowita - rynkowa cena sprawnego sprzętu w PLN>,
  "negotiation_target": <liczba całkowita - sugerowana cena negocjacyjna na Vinted w PLN>,
  "market_liquidity": "<BARDZO SZYBKO | ŚREDNIO | NISKA PŁYNNOŚĆ>",
  "risk_assessment": "<NISKIE - ... | ŚREDNIE - ... | WYSOKIE - ...>",
  "salvage_value": <liczba całkowita - wartość na części/dawca w PLN>,
  "fault_analysis": "<zwięzła diagnoza usterki lub 'Sprzęt sprawny'>",
  "repair_difficulty": "<ŁATWA | ŚREDNIA | TRUDNA | Brak>",
  "repair_steps": ["1. ...", "2. ..."],
  "estimated_parts_cost": <liczba całkowita - koszt części w PLN, 0 dla OKAZJA_FLIP>,
  "estimated_net_profit": <liczba całkowita - zysk czysty w PLN>,
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
    profit_threshold_flip: float = PROFIT_THRESHOLD_FLIP_PLN,
    profit_threshold_repair: float = PROFIT_THRESHOLD_REPAIR_PLN,
    shipping_cost: float = SHIPPING_COST_PLN
) -> EvaluationResult:
    """Send listing details to Ollama API (Qwen 2.5) for dual deal analysis (OKAZJA_FLIP vs OKAZJA_NAPRAWA)."""
    user_prompt = f"""Przeanalizuj poniższe ogłoszenie pod kątem dwóch typów okazji (Czysty Flip vs Sprzęt Do Naprawy):

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

        raw_deal_type = str(data.get("deal_type", "BRAK_ZYSKU")).strip().upper()
        if "FLIP" in raw_deal_type:
            deal_type = "OKAZJA_FLIP"
        elif "NAPRAWA" in raw_deal_type:
            deal_type = "OKAZJA_NAPRAWA"
        else:
            deal_type = "BRAK_ZYSKU"

        try:
            raw_score = int(data.get("deal_score", 1))
            deal_score = max(1, min(10, raw_score))
        except (ValueError, TypeError):
            deal_score = 1

        # Financials
        market_val_raw = data.get("estimated_market_value") or data.get("estimated_resale_price_pln")
        try:
            market_val = int(market_val_raw if market_val_raw is not None else listing.price)
        except (ValueError, TypeError):
            market_val = int(listing.price)

        parts_cost_raw = data.get("estimated_parts_cost") or data.get("estimated_repair_cost") or data.get("estimated_parts_cost_pln")
        try:
            parts_cost = int(parts_cost_raw if parts_cost_raw is not None else 0)
        except (ValueError, TypeError):
            parts_cost = 0

        if deal_type == "OKAZJA_FLIP":
            parts_cost = 0

        total_expenses = listing.price + shipping_cost + parts_cost
        calculated_net_profit = int(market_val - total_expenses)

        if total_expenses > 0:
            roi_percentage = int((calculated_net_profit / total_expenses) * 100)
        else:
            roi_percentage = 0

        # Strategy & Risk
        try:
            neg_target = int(data.get("negotiation_target", int(listing.price * 0.85)))
        except (ValueError, TypeError):
            neg_target = int(listing.price * 0.85)

        market_liquidity = str(data.get("market_liquidity") or "ŚREDNIO").strip().upper()
        if "SZYBKO" in market_liquidity:
            market_liquidity = "BARDZO SZYBKO"
        elif "NISKA" in market_liquidity:
            market_liquidity = "NISKA PŁYNNOŚĆ"
        else:
            market_liquidity = "ŚREDNIO"

        risk_assessment = str(data.get("risk_assessment") or "NISKIE - standardowe ryzyko zakupu")

        try:
            salvage_val = int(data.get("salvage_value", int(listing.price * 0.4)))
        except (ValueError, TypeError):
            salvage_val = int(listing.price * 0.4)

        # Technical analysis
        fault_analysis = str(data.get("fault_analysis") or "Brak usterki / Sprzęt sprawny")
        repair_difficulty = str(data.get("repair_difficulty") or "ŁATWA").strip().upper()
        if "TRUDNA" in repair_difficulty:
            repair_difficulty = "TRUDNA"
        elif "ŚREDNIA" in repair_difficulty or "SREDNIA" in repair_difficulty:
            repair_difficulty = "ŚREDNIA"
        elif "ŁATWA" in repair_difficulty or "LATWA" in repair_difficulty:
            repair_difficulty = "ŁATWA"
        else:
            repair_difficulty = "Brak"

        repair_steps_raw = data.get("repair_steps", ["1. Standardowa weryfikacja"])
        if isinstance(repair_steps_raw, list):
            repair_steps = [str(step) for step in repair_steps_raw]
        else:
            repair_steps = str(repair_steps_raw)

        reasoning = str(data.get("reasoning") or data.get("recommendation_reason") or "Brak uzasadnienia")

        # Python qualification criteria logic for Discord alerts:
        # For "OKAZJA_FLIP": net_profit >= 80 PLN
        # For "OKAZJA_NAPRAWA": net_profit >= 100 PLN (after parts cost)
        is_profitable = False
        if deal_type == "OKAZJA_FLIP" and calculated_net_profit >= profit_threshold_flip:
            is_profitable = True
        elif deal_type == "OKAZJA_NAPRAWA" and calculated_net_profit >= profit_threshold_repair:
            is_profitable = True

        # Python enforcement of Blacklisted Hardware Series / Liquid damage
        full_text = f"{listing.title} {listing.description} {fault_analysis}".lower()
        for pattern in BLACK_LIST_PATTERNS:
            if re.search(pattern, full_text):
                logger.info(f"Overriding deal_type for {listing.id} to BRAK_ZYSKU due to blacklisted defect pattern '{pattern}'")
                deal_type = "BRAK_ZYSKU"
                deal_score = min(deal_score, 2)
                is_profitable = False
                break

        return EvaluationResult(
            item_title=item_title,
            category=category,
            deal_type=deal_type,
            deal_score=deal_score,
            estimated_market_value=market_val,
            estimated_parts_cost=parts_cost,
            estimated_net_profit=calculated_net_profit,
            roi_percentage=roi_percentage,
            negotiation_target=neg_target,
            market_liquidity=market_liquidity,
            risk_assessment=risk_assessment,
            salvage_value=salvage_val,
            fault_analysis=fault_analysis,
            repair_difficulty=repair_difficulty,
            repair_steps=repair_steps,
            is_profitable=is_profitable,
            reasoning=reasoning
        )

    except Exception as e:
        logger.error(f"Error evaluating listing {listing.id} via Ollama API: {e}")
        return EvaluationResult(
            item_title=listing.title,
            category=listing.category,
            deal_type="BRAK_ZYSKU",
            deal_score=1,
            estimated_market_value=int(listing.price),
            estimated_parts_cost=0,
            estimated_net_profit=0,
            roi_percentage=0,
            negotiation_target=int(listing.price),
            market_liquidity="NISKA PŁYNNOŚĆ",
            risk_assessment="WYSOKIE - Błąd analizy API",
            salvage_value=0,
            fault_analysis="Błąd analizy API",
            repair_difficulty="TRUDNA",
            repair_steps=["Błąd analizy API"],
            is_profitable=False,
            reasoning=f"Błąd podczas analizy przez Ollama API: {e}"
        )
    finally:
        if should_close:
            client.close()
