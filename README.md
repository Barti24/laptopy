# Multi-Category Electronics Repair & Flipping Monitor (Vinted + Ollama Qwen 2.5)

Skrypt w języku Python służący do automatycznego monitorowania ogłoszeń sprzętu elektronicznego na portalu **Vinted.pl** (ogłoszenia z OLX tymczasowo wyłączone), z pre-filtracją ofert oraz zaawansowaną analizą opłacalności zakupu i naprawy przy użyciu lokalnego modelu LLM **Ollama (Qwen 2.5)**.

---

## ⚡ Pre-Filtracja Ofert (Przed zapytaniem do AI)

Aby znacząco przyspieszyć działanie bota i oszczędzać czas generowania odpowiedzi przez Ollamę, oferty przechodzą przez szybką dwustopniową pre-filtrację w kodzie Pythona:

1. **Limit Ceny Maksymalnej (`max_price`) per kategoria**:
   - Laptopy: max **800 PLN**
   - Konsole: max **600 PLN**
   - Karty graficzne: max **700 PLN**
   - Drukarki 3D: max **500 PLN**
   - Sprzęt Audio: max **600 PLN**
2. **Filtr Słów Kluczowych Usterki (`FAULT_KEYWORDS`)**:
   Tytuł lub opis musi zawierać przynajmniej jedno ze słów (case-insensitive):
   `["uszkodzon", "do naprawy", "brak", "nietestowan", "nie włącza", "nie dziala", "pęknięt", "na części", "stacjonarn", "hasło", "icloud", "bios", "artefakt", "zalany"]`

---

## 🛡️ Obejście Blokad 403 (curl_cffi & Chrome Impersonation)

Skraper wykorzystuje bibliotekę **`curl_cffi`** z opcją `impersonate="chrome120"` oraz symulacją pełnego TLS fingerprinting i nagłówków przeglądarki Chrome do bezproblemowego pobierania ogłoszeń bez blokad HTTP 403:
- **Vinted**: Posiada mechanizm wstępnego pobierania ciasteczek sesyjnych (`_vinted_fr_session`) z adresu `https://www.vinted.pl/` przed wykonaniem zapytania do API `/api/v2/catalog/items`.

---

## 🧠 Analiza Naprawy i Wycena przez Ollama (Qwen 2.5)

Oferty spełniające pre-filtrację trafiają do API Ollama (z wyłączonym limitu czasu `timeout=None`), które zwraca odpowiedź w ścisłym formacie JSON:
```json
{
  "item_title": "PS4 Slim 500GB",
  "category": "Konsole",
  "detected_fault": "Uszkodzony laser/napęd oraz zapchane chłodzenie",
  "difficulty_level": "Prosta",
  "estimated_parts_cost_pln": 50,
  "estimated_market_value_working_pln": 500,
  "net_profit_pln": 185,
  "roi_percentage": 58,
  "is_profitable": true,
  "recommendation_reason": "Prosta wymiana lasera i czyszczenie dają 185 zł zysku na czysto."
}
```

### 📐 Wzory i Warunki Opłacalności:
- **Koszt wysyłki**: Stały koszt 15 PLN.
- **Zysk na czysto (Net Profit)**:
  `Wartość Rynkowa po Naprawie - (Cena Zakupu + 15 PLN Wysyłka + Koszt Części)`
- **ROI**:
  `(Net Profit / Całkowite Wydatki) * 100`
- **Kryterium Opłacalności (`is_profitable: true`)**:
  - `net_profit_pln >= 100 PLN`
  - Brak ryzyka trwałego uszkodzenia BGA / płyty głównej / CPU / GPU.
  - **Automatyczna korekta**: Jeśli w opisie wykrytej usterki widnieje "brak usterki" lub "sprzęt sprawny", Python wymusza `is_profitable = False`.

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
