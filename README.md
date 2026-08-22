# Multi-Category Electronics Repair & Flipping Monitor (Vinted + Ollama Qwen 2.5 + Live Market Search)

Skrypt w języku Python służący do automatycznego monitorowania ogłoszeń sprzętu elektronicznego na portalu **Vinted.pl** (ogłoszenia z OLX tymczasowo wyłączone), z bezproblemową obsługą cookie bootstrappingu i retry w przypadku HTTP 403, wsparciem dla opcjonalnych serwerów Proxy (`PROXY_URL`), hybrydową pre-filtracją ofert ze ścisłym porządkiem czarnych list, automatycznym wyszukiwaniem cen rynkowych w sieci (DuckDuckGo Search via `ddgs`) oraz ustrukturyzowaną analizą rzeczoznawczą przy użyciu **Ollama (`qwen2.5:7b`)**.

---

## ⚡ Ścisła Kolejność Hybrydowej Pre-Filtracji Ofert

Przed przekazaniem oferty do analizy AI, kod Pythona w funkcji `passes_pre_filter` wykonuje szybki przesiew według ściśle ustalonej kolejności:

1. **Krok 1: Limit Ceny Maksymalnej (`max_price`)**:
   - Laptopy: max **1200 PLN** | Konsole: max **900 PLN** | Karty graficzne: max **1000 PLN** | Drukarki 3D: max **800 PLN** | Audio: max **600 PLN**
2. **Krok 2: BEZWZGLĘDNE CZARNE LISTY (Przed Auto-Pass!)**:
   - **Zabawki i sprzęt dla dzieci (`EXCLUDE_TOYS`)**: `["edukacyjny", "edykacyjny", "zabawka", "zabawkowy", "dla dzieci", "interaktywny", "fisher price", "hello kitty", "barbie"]`.
   - **Komponenty i części laptopowe (`EXCLUDE_PARTS`)**: `["ram", "procesor", "processzorok", "cpu", "dysk", "ssd", "hdd", "matryca", "płyta główna", "plyta glowna", "obudowa", "klawiatura do", "bateria do"]`.
   - *Jeśli ogłoszenie zawiera słowo z czarnej listy, zostaje odrzucone NATYCHMIAST (nawet jeśli cena < 150 PLN).*
3. **Krok 3: Tanie oferty (AUTO-PASS)**:
   - Laptopy < 250 PLN, Konsole < 150 PLN, Karty graficzne < 150 PLN, Drukarki 3D < 200 PLN, Sprzęt Audio < 150 PLN.
4. **Krok 4: Słowa Kluczowe Usterek (`FAULT_KEYWORDS`)**:
   - np. `uszkodz`, `zepsut`, `nietest`, `dawc`, `napraw`, `brak`, `wada`, `pękn`, `zalaw`, `nie włącza`, `artefakt`, `hasło`, `bios`, `część`, `stan`.

---

## 🌐 Live Wyszukiwanie Cen w Sieci (DuckDuckGo Search via `ddgs`)

Przed wysłaniem ogłoszenia do Ollamy, moduł `market_search.py` (używający nowoczesnego pakietu `ddgs`) pobiera w czasie rzeczywistym **top 3 wyniki z wyszukiwarki DuckDuckGo** dla zapytania `f"{tytul_przedmiotu} cena OLX Allegro"`. Fragmenty z opisami i cenami z sieci są przekazywane do prompta w sekcji `WYNIKI Z WYSZUKIWARKI RYNKOWEJ`.

### Zasadnicze reguły prompta:
- Model wycenia wartość rynkową **WYŁĄCZNIE** na podstawie wyników z wyszukiwarki rynkowej.
- Jeśli wyniki lub opis wskazują, że sprzęt ma wartość rynkową **poniżej 50 PLN**, skrypt automatycznie ustawia `verdict: BRAK_ZYSKU`.

---

## ⏱️ Ograniczanie Natężenia Ruchu i Zabezpieczenia (Rate-Limiting)

1. **Czas Cyklu (`FETCH_INTERVAL_SECONDS = 600`)**: Częstotliwość uruchamiania pętli sprawdzania wynosi **10 minut** (600 sekund).
2. **Głębokość Skanowania (`MAX_PAGES_PER_CATEGORY = 2`)**: Domyślna głębokość skanowania wynosi **2 strony per kategoria** w automatycznym cyklu.
3. **Throttling & Jitter**:
   - Między stronami w danej kategorii: losowe opóźnienie **1.5s – 3.0s**.
   - Między poszczególnymi kategoriami: losowe opóźnienie **3.0s – 6.0s**.
4. **Przerwa Nocna (01:00 – 06:00)**: Jeśli godzina systemowa znajduje się w przedziale 01:00–06:00, skrypt automatycznie pomija pętlę skanowania i uśnie na **30 minut** (`time.sleep(1800)`).

---

## 🛡️ Dedykowana Obsługa Sesji, Proxy i Obejście 403 (Cookie Bootstrapping & Retry)

Skraper Vinted (`scrapers/vinted.py`) stosuje zaawansowane mechanizmy radzenia sobie z ochroną przed botami:
1. **Opcjonalne Proxy (`PROXY_URL`)**: Obsługa zmiennej środowiskowej `PROXY_URL` (np. `http://user:pass@host:port` lub `socks5://host:port`).
2. **Cookie Bootstrapping (`bootstrap_vinted_session`)**: Odwiedzanie strony głównej `https://www.vinted.pl/` przy użyciu `curl_cffi.requests.Session(impersonate="chrome120")` i nagłówków nawigacyjnych Chrome 120.
3. **Automatyczny Retry po 403 z Dedykowaną Obsługą Wyjątków**: Obsługa odświeżania ciasteczek przy wyłapaniu `HTTPError` / `RequestException`.

---

## 🧠 Klasyfikacja i Wycena Rzeczoznawcza (`qwen2.5:7b`)

Model Qwen 2.5 dokonywuje oceny i klasyfikuje ofertę do jednego z dwóch typów okazji:
- 🎯 **`OKAZJA_FLIP` (Czysty Flip)**: net_profit >= 80 PLN.
- 🛠️ **`OKAZJA_NAPRAWA` (Sprzęt Do Naprawy)**: net_profit >= 100 PLN (po potrąceniu kosztów części i 20 PLN wysyłki).

### 📋 JSON Schema Odpowiedzi:
```json
{
  "item_title": "PS4 Slim 500GB",
  "category": "Konsole",
  "deal_type": "OKAZJA_NAPRAWA",
  "deal_score": 9,
  "estimated_market_value": 550,
  "negotiation_target": 170,
  "market_liquidity": "BARDZO SZYBKO",
  "risk_assessment": "NISKIE - standardowa wymiana laseru",
  "salvage_value": 250,
  "fault_analysis": "Uszkodzony laser napędu KES-496",
  "repair_difficulty": "ŁATWA",
  "repair_steps": ["1. Wymiana laseru KES-496", "2. Czyszczenie obudowy"],
  "estimated_parts_cost": 40,
  "estimated_net_profit": 260,
  "reasoning": "Tani laser i bardzo niska cena zakupu zapewniają wysoki zysk netto."
}
```

---

## 🔔 Powiadomienia Discord & Telegram

Powiadomienia na Discordzie wysyłane są w ustrukturyzowanym szablonie:
- 🎯 **[CZYSTY FLIP]** lub 🛠️ **[DO NAPRAWY]**
- 💰 **Finanse:** Cena Vinted | Cena Rynkowa | Szacowany Zysk Czysty (ROI %)
- 🎯 **Strategia:** Sugerowana oferta negocjacyjna na Vinted | Płynność rynku
- 🛠️ **Diagnoza i Plan:** Diagnoza | Trudność | Koszt części | Plan
- 🛡️ **Ryzyko i Plan B:** Poziom ryzyka | Wartość na części (Plan B) | Uzasadnienie Qwen 2.5

---

## 🛠️ Wymagania i Uruchomienie

### 1. Wymagania
- Python 3.10+
- Środowisko POSIX (Linux / Docker / Proxmox LXC)
- [Ollama](https://ollama.com/) z pobranym modelem `qwen2.5:7b`:
  ```bash
  ollama pull qwen2.5:7b
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
