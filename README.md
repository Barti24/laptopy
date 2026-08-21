# Multi-Category Electronics Repair & Flipping Monitor (Vinted + Ollama Qwen 2.5)

Skrypt w języku Python służący do automatycznego monitorowania ogłoszeń sprzętu elektronicznego na portalu **Vinted.pl** (ogłoszenia z OLX tymczasowo wyłączone), z pre-filtracją ofert oraz zaawansowaną dynamiczną analizą opłacalności zakupu i naprawy przy użyciu lokalnego modelu LLM **Ollama (Qwen 2.5)**.

---

## ⚡ Pre-Filtracja Ofert (Przed zapytaniem do AI)

Przed przekazaniem oferty do analizy AI, kod Pythona wykonuje szybki przesiew:

1. **Limit Ceny Maksymalnej (`max_price`) per kategoria**:
   - Laptopy: max **800 PLN**
   - Konsole: max **600 PLN**
   - Karty graficzne: max **700 PLN**
   - Drukarki 3D: max **500 PLN**
   - Sprzęt Audio: max **600 PLN**
2. **Słowa Kluczowe Usterek (`FAULT_KEYWORDS`)**:
   Tytuł lub opis musi zawierać przynajmniej jedno ze słów (case-insensitive):
   `["uszkodzon", "do naprawy", "brak", "nietestowan", "nie włącza", "nie dziala", "pęknięt", "na części", "stacjonarn", "hasło", "icloud", "bios", "artefakt", "zalany"]`

---

## 🧠 Dynamiczna Analiza i Wycena przez Ollama (Qwen 2.5)

Model Qwen 2.5 dynamicznie analizuje specyfikację (np. DDR3 vs DDR4, NVMe vs SATA, typ matrycy, model i generację) i oszacowuje koszt części zamiennych oraz wartość odsprzedaży na rynku wtórnym:

```json
{
  "item_title": "PS4 Slim 500GB",
  "category": "Konsole",
  "detected_fault": "Uszkodzony laser/napęd KES-496 oraz zapchane chłodzenie",
  "difficulty_level": "Prosta",
  "estimated_parts_cost_pln": 50,
  "estimated_resale_price_pln": 500,
  "net_profit_pln": 170,
  "roi_percentage": 51,
  "is_profitable": true,
  "recommendation_reason": "Wymiana lasera KES-496 i czyszczenie dają 170 zł zysku na czysto."
}
```

### 📐 Wzory i Zasady Finansowe:
- **Koszt wysyłki i obsługi**: Stałe **30 PLN**.
- **Zysk Na Czysto (Net Profit)**:
  `Oszacowana Cena Sprzedaży (estimated_resale_price_pln) - (Cena Zakupu + 30 PLN + Szacowany Koszt Części)`
- **ROI**:
  `(Net Profit / Całkowite Wydatki) * 100`

### 🚫 Bezwzględne Odrzucenie (Strict Rejection -> `is_profitable = false`):
- Brak jednoznacznego opisu usterki, opis "nietestowany", "stan nieznany", "stan nieokreślony" lub "stan idealny / brak usterki".
- Sprzęt po zalaniu płynami / cieczą / z korozją.
- Czarne listy wadliwych serii:
  - **MacBook Pro 15"/17" z lat 2011–2012** (wadliwe układy GPU Radeon)
  - **Xbox 360 Xenon / Zephyr** (błędy RROD / wadliwe układy BGA)

---

## 🔔 Powiadomienia Discord & Telegram

Powiadomienia na Discordzie wysyłane są w formie estetycznych kart Embed:
- **Zielona ramka**: Urządzenia opłacalne (`is_profitable: true`, zysk netto >= 100 zł),
- **Żółta ramka**: Oferty ryzykowne lub o niskiej marży.

---

## 🛠️ Wymagania i Uruchomienie

### 1. Wymagania
- Python 3.10+
- Środowisko POSIX (Linux / Docker / Proxmox LXC)
- [Ollama](https://ollama.com/) z pobranym modelem `qwen2.5:14b`:
  ```bash
  ollama pull qwen2.5:14b
  ```

### 2. Instalacja zależności
```bash
pip install -r requirements.txt
```

### 3. Uruchomienie skryptu

- **Tryb jednorazowy z podglądem (--dry-run)**:
  ```bash
  python3 main.py --once --dry-run
  ```
- **Praca w pętli ciągłej**:
  ```bash
  python3 main.py
  ```

### 4. Testy Jednostkowe
```bash
pytest
```
