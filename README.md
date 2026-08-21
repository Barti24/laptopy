# Multi-Category Electronics Repair & Flipping Monitor (Vinted + Ollama Qwen 2.5)

Skrypt w języku Python służący do automatycznego monitorowania ogłoszeń sprzętu elektronicznego na portalu **Vinted.pl** (ogłoszenia z OLX tymczasowo wyłączone), z hybrydową pre-filtracją ofert, przyrostowym skanowaniem historii (Deep Scan) oraz ustrukturyzowaną analizą rzeczoznawczą dla dwóch typów okazji przy użyciu **Ollama (Qwen 2.5)**.

---

## ⚡ Hybrydowa Pre-Filtracja Ofert (Przed zapytaniem do AI)

Aby zmaksymalizować wyłapywanie okazji i oszczędzać moc obliczeniową, oferta przekazywana jest do oceny przez Ollamę, jeśli mieści się w cenie maksymalnej ORAZ spełnia przynajmniej **JEDEN** z warunków:

1. **Jest ofertą bardzo tanią (AUTO-PASS)**:
   - Laptopy: **< 250 PLN** (max 1200 PLN)
   - Konsole: **< 150 PLN** (max 900 PLN)
   - Karty graficzne: **< 150 PLN** (max 1000 PLN)
   - Drukarki 3D: **< 200 PLN** (max 800 PLN)
   - Sprzęt Audio: **< 150 PLN** (max 600 PLN)
2. **Zawiera w tytule lub opisie rdzeń słowa kluczowego usterki (`FAULT_KEYWORDS`)**:
   `["uszkodz", "zepsut", "nietest", "dawc", "napraw", "brak", "wada", "wadliw", "pękn", "zalaw", "zalani", "restart", "nie włącza", "nie wlacz", "nie dziala", "nie działa", "rozbit", "spalon", "hasło", "bios", "artefakt", "skaza", "część", "stan"]`

---

## 🧠 Klasyfikacja i Wycena Rzeczoznawcza przez Ollama (Qwen 2.5)

Model Qwen 2.5 dokonywuje dokładnej oceny i klasyfikuje ofertę do jednego z dwóch typów okazji:

1. 🎯 **`OKAZJA_FLIP` (Czysty Flip)**:
   - Sprzęt sprawny/nowy sprzedawany bardzo tanio.
   - Koszt części = 0 PLN.
   - Wymagany zysk czysty: `estimated_net_profit >= 80 PLN`.
2. 🛠️ **`OKAZJA_NAPRAWA` (Sprzęt Do Naprawy)**:
   - Sprzęt posiadający wadę, uszkodzenie lub brak części z potencjałem zysku po naprawie.
   - Wymagany zysk czysty po potrąceniu kosztów części i 20 PLN wysyłki: `estimated_net_profit >= 100 PLN`.

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

## 🔔 Bogate Powiadomienia Discord

Powiadomienia na Discordzie wysyłane są w ustrukturyzowanym szablonie zawierającym sekcje:
- 🎯 **[CZYSTY FLIP]** lub 🛠️ **[DO NAPRAWY]**
- 💰 **Finanse:** Cena Vinted | Cena Rynkowa | Szacowany Zysk Czysty (ROI %)
- 🎯 **Strategia:** Sugerowana oferta negocjacyjna na Vinted | Płynność rynku
- 🛠️ **Diagnoza i Plan:** (sekcja widoczna dla sprzętu do naprawy) Diagnoza | Trudność | Koszt części | Plan
- 🛡️ **Ryzyko i Plan B:** Poziom ryzyka | Wartość na części (Plan B / dawca) | Uzasadnienie Qwen 2.5

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
