# Multi-Category Electronics Repair & Flipping Monitor (Vinted + Ollama Qwen 2.5 + Live Market Search)

Skrypt w języku Python służący do automatycznego monitorowania ogłoszeń sprzętu elektronicznego na portalu **Vinted.pl** (ogłoszenia z OLX tymczasowo wyłączone), z bezproblemową obsługą cookie bootstrappingu i retry w przypadku HTTP 403, dwustopniową pre-filtracją (wykluczanie części i zabawek), automatycznym wyszukiwaniem cen rynkowych w sieci (DuckDuckGo Search) oraz ustrukturyzowaną analizą rzeczoznawczą przy użyciu **Ollama (`qwen2.5:7b`)**.

---

## 🛡️ Dedykowana Obsługa Sesji i Obejście 403 (Cookie Bootstrapping & Retry)

Skraper Vinted (`scrapers/vinted.py`) stosuje zaawansowane mechanizmy radzenia sobie z ochroną przed botami:
1. **Cookie Bootstrapping (`bootstrap_vinted_session`)**: Przed pierwszym zapytaniem do API catalog items, klient odwiedza stronę główną `https://www.vinted.pl/`, pobierając aktualne ciasteczka sesyjne (`_vinted_fr_session`).
2. **Realistyczne Nagłówki Chrome (`VINTED_HEADERS`)**: Zapytania zawierają nagłówki prawdziwej przeglądarki Chrome 120, w tym `Referer: https://www.vinted.pl/`, `Accept-Language: pl-PL` oraz nagłówki `Sec-Ch-Ua`.
3. **Automatyczny Retry po 403**: W przypadku napotkania statusu HTTP 403 Forbidden, skraper odświeża sesję (ponownie pobiera ciasteczka ze strony głównej) i ponawia próbę do 2 razy z opóźnieniem.
4. **Losowe Opóźnienia (Throttling)**: Pomiędzy zapytaniami do kolejnych stron oraz kategorii stosowane są losowe opóźnienia (`1.5s - 3.0s` / `2.0s - 4.0s`), co zapobiega nakładaniu blokad natężenia ruchu.

---

## ⚡ Hybrydowa Pre-Filtracja Ofert (Przed zapytaniem do AI)

Przed przekazaniem oferty do analizy AI, kod Pythona wykonuje szybki przesiew:

1. **Limit Ceny Maksymalnej (`max_price`) per kategoria**:
   - Laptopy: max **1200 PLN** | Konsole: max **900 PLN** | Karty graficzne: max **1000 PLN** | Drukarki 3D: max **800 PLN** | Audio: max **600 PLN**
2. **Czarna Lista Zabawek i Sprzętu dla Dzieci (`EXCLUDE_TOYS`)**:
   Odrzucanie ogłoszeń zabawek dla dzieci: `["zabawka", "zabawkowy", "edukacyjny", "dla dzieci", "hello kitty", "barbie", "fisher price", "interaktywny", "grający", "minnie", "paws", "psi patrol"]`.
3. **Wykluczenie Części i Komponentów (`EXCLUDE_PARTS`)**:
   Dla kategorii Laptopy odrzucane są ogłoszenia dotyczące samych części zamiennych: `["ram", "procesor", "processzorok", "cpu", "dysk", "ssd", "hdd", "matryca", "płyta główna", "plyta glowna", "obudowa", "klawiatura do", "bateria do"]`.
4. **Warunki kwalifikacji do AI**:
   - **Tanie oferty (AUTO-PASS)**: Laptopy < 250 PLN, Konsole < 150 PLN, Karty graficzne < 150 PLN, Drukarki 3D < 200 PLN, Sprzęt Audio < 150 PLN.
   - **Lub Słowa Kluczowe Usterek (`FAULT_KEYWORDS`)**: np. `uszkodz`, `zepsut`, `nietest`, `dawc`, `napraw`, `brak`, `wada`, `pękn`, `zalaw`, `nie włącza`, `artefakt`, `hasło`, `bios`, `część`, `stan`.

---

## 🌐 Live Wyszukiwanie Cen w Sieci (DuckDuckGo Search)

Przed wysłaniem ogłoszenia do Ollamy, moduł `market_search.py` pobiera w czasie rzeczywistym **top 3 wyniki z wyszukiwarki DuckDuckGo** dla zapytania `f"{tytul_przedmiotu} cena OLX Allegro"`. Fragmenty z opisami i cenami z sieci są przekazywane do prompta w sekcji `WYNIKI Z WYSZUKIWARKI RYNKOWEJ`.

### Zasadnicze reguły prompta:
- Model wycenia wartość rynkową **WYŁĄCZNIE** na podstawie wyników z wyszukiwarki rynkowej.
- Jeśli wyniki lub opis wskazują, że sprzęt ma wartość rynkową **poniżej 50 PLN**, skrypt automatycznie ustawia `verdict: BRAK_ZYSKU`.

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
