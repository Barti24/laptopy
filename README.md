# Multi-Category Electronics Repair & Flipping Monitor (Vinted / OLX + Ollama Qwen 2.5)

Skrypt w języku Python służący do automatycznego monitorowania ogłoszeń sprzętu elektronicznego na portalach **OLX.pl** oraz **Vinted.pl**, z zaawansowaną analizą opłacalności zakupu i naprawy przy użyciu lokalnego modelu LLM **Ollama (Qwen 2.5)**.

---

## 🛡️ Obejście Blokad 403 (curl_cffi & Chrome Impersonation)

Skrapery wykorzystują bibliotekę **`curl_cffi`** z opcją `impersonate="chrome120"` oraz symulacją pełnego TLS fingerprinting i nagłówków przeglądarki Chrome do bezproblemowego pobierania ogłoszeń bez blokad HTTP 403:
- **Vinted**: Posiada mechanizm wstępnego pobierania ciasteczek sesyjnych (`_vinted_fr_session`) z adresu `https://www.vinted.pl/` przed wykonaniem zapytania do API `/api/v2/catalog/items`.
- **OLX**: Pobiera i parsuje osadzone dane `__PRERENDERED_STATE__` lub strukturę HTML DOM z pełnymi nagłówkami przeglądarki.

---

## 🚀 Wszechstronne Kategorie Elektroniki

Skrypt obsługuje słowa kluczowe i dedykowane filtry wyszukiwania dla wielu kategorii urządzeń:
- **Laptopy**: np. `thinkpad`, `dell latitude`, `uszkodzony`, `brak dysku`
- **Konsole**: np. `ps4`, `xbox one`, `switch`, `nie czyta płyt`, `głośno chodzi`
- **Karty graficzne**: np. `rtx`, `gtx`, `rx`, `artefakty`, `przegrzewa się`
- **Drukarki 3D**: np. `ender`, `neptune`, `zatkana`, `brak serwa`
- **Sprzęt Audio / Amplitunery**: np. `amplituner`, `brak dźwięku`, `trzeszczy`, `uszkodzony kanał`

---

## 🧠 Analiza Naprawy i Wycena przez Ollama (Qwen 2.5)

Dla każdego ogłoszenia model AI zwraca odpowiedź w ścisłym formacie JSON zawierającą:
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

### 📐 Wzory Finansowe:
- **Koszt wysyłki**: Stały koszt 15 PLN.
- **Zysk na czysto (Net Profit)**:
  `Wartość Rynkowa po Naprawie - (Cena Zakupu + 15 PLN Wysyłka + Koszt Części)`
- **ROI**:
  `(Net Profit / Całkowite Wydatki) * 100`
- **Kryterium Opłacalności (`is_profitable: true`)**:
  Net Profit >= 100 PLN oraz brak nieopłacalnego ryzyka uszkodzenia rdzenia BGA / płyty głównej / CPU / GPU.

---

## 🔔 Powiadomienia Discord & Telegram

Powiadomienia na Discordzie wysyłane są w formie estetycznych kart Embed:
- **Zielona ramka**: Urządzenia opłacalne (`is_profitable: true`, zysk netto >= 100 zł),
- **Żółta ramka**: Oferty ryzykowne lub o niskiej marży.
- Każde powiadomienie zawiera:
  - Wykrytą usterkę i trudność naprawy,
  - Cena zakupu, koszt części oraz szacowaną wartość po naprawie,
  - **Zysk na czysto (Net Profit)** oraz **ROI (%)**,
  - Rekomendację AI,
  - **Bezpośredni link** do ogłoszenia na OLX/Vinted.

---

## 🛠️ Wymagania i Uruchomienie

### 1. Wymagania
- Python 3.10+
- Environment POSIX (Linux / Docker / Proxmox LXC)
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
