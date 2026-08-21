# Multi-Category Electronics Repair & Flipping Monitor (Vinted + Ollama Qwen 2.5)

Skrypt w języku Python służący do automatycznego monitorowania ogłoszeń sprzętu elektronicznego na portalu **Vinted.pl** (ogłoszenia z OLX tymczasowo wyłączone), z dwustopniową pre-filtracją ofert (wykluczanie części zamiennych i obudów), przyrostowym skanowaniem historii (Deep Scan) oraz ustrukturyzowaną analizą rzeczoznawczą przy użyciu **Ollama (`qwen2.5:7b`)**.

---

## ⚡ Hybrydowa Pre-Filtracja Ofert z Wykluczeniem Części

Przed przekazaniem oferty do analizy AI, kod Pythona wykonuje szybki przesiew:

1. **Limit Ceny Maksymalnej (`max_price`) per kategoria**:
   - Laptopy: max **1200 PLN**
   - Konsole: max **900 PLN**
   - Karty graficzne: max **1000 PLN**
   - Drukarki 3D: max **800 PLN**
   - Sprzęt Audio: max **600 PLN**
2. **Wykluczenie Części i Komponentów (`EXCLUDE_PARTS`)**:
   Dla kategorii Laptopy odrzucane są ogłoszenia dotyczące samych części zamiennych, takich jak: `["ram", "procesor", "processzorok", "cpu", "dysk", "ssd", "hdd", "matryca", "płyta główna", "plyta glowna", "obudowa", "klawiatura do", "bateria do"]`.
3. **Warunki kwalifikacji do AI**:
   - **Tanie oferty (AUTO-PASS)**: Laptopy < 250 PLN, Konsole < 150 PLN, Karty graficzne < 150 PLN, Drukarki 3D < 200 PLN, Sprzęt Audio < 150 PLN.
   - **Lub Słowa Kluczowe Usterek (`FAULT_KEYWORDS`)**: np. `uszkodz`, `zepsut`, `nietest`, `dawc`, `napraw`, `brak`, `wada`, `pękn`, `zalaw`, `nie włącza`, `artefakt`, `hasło`, `bios`, `część`, `stan`.

---

## ⚙️ Konfiguracja Ollama (`qwen2.5:7b`) i Limit Cansu (600s)

- **Model Domyślny**: `qwen2.5:7b` (możliwość nadpisania przez zmienną środowiskową `MODEL_NAME` lub `OLLAMA_MODEL`).
- **Limit Czasu**: Usługa HTTP korzysta ze sztywnego limitu `timeout=600.0` (10 minut). W przypadku przekroczenia czasu zapytanie jest bezpiecznie pomijane (`httpx.TimeoutException`), logowane i skrypt przechodzi do kolejnej oferty.
- **Parametry Generowania**:
  ```json
  "options": {
      "num_predict": 300,
      "temperature": 0.1,
      "stop": ["}\n", "}]"]
  }
  ```

---

## 🧠 Klasyfikacja i Wycena Rzeczoznawcza

Model Qwen 2.5 dokonywuje oceny i klasyfikuje ofertę do jednego z dwóch typów okazji:

1. 🎯 **`OKAZJA_FLIP` (Czysty Flip)**:
   - Sprzęt sprawny/nowy sprzedawany bardzo tanio (net_profit >= 80 PLN).
2. 🛠️ **`OKAZJA_NAPRAWA` (Sprzęt Do Naprawy)**:
   - Sprzęt z wadą lub brakiem części (net_profit >= 100 PLN po potrąceniu kosztów części i 20 PLN wysyłki).

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
