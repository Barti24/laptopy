# Multi-Category Electronics Repair & Flipping Monitor (Vinted + Ollama Qwen 2.5)

Skrypt w języku Python służący do automatycznego monitorowania ogłoszeń sprzętu elektronicznego na portalu **Vinted.pl** (ogłoszenia z OLX tymczasowo wyłączone), z hybrydową pre-filtracją ofert, ustrukturyzowanym systemem punktacji AI (Qwen 2.5) oraz przyrostowym skanowaniem historii (Deep Scan).

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

## 🧠 Punktacja i Werdykt AI przez Ollama (Qwen 2.5)

Model Qwen 2.5 przeanalizuje specyfikację sprzętu i zwraca ustrukturyzowaną odpowiedź w formacie JSON:

```json
{
  "item_title": "PS4 Slim 500GB",
  "category": "Konsole",
  "detected_fault": "Uszkodzony napęd laser KES-496 oraz zapchane chłodzenie",
  "difficulty_level": "Prosta",
  "deal_score": 9,
  "verdict": "OKAZJA",
  "estimated_market_value": 550,
  "estimated_repair_cost": 40,
  "reasoning": "Niska cena zakupu i tani laser dają 280 zł zysku na czysto."
}
```

### 📊 Skala Oceny (`deal_score` & `verdict`):
- **Score 8–10 (`verdict: "OKAZJA"`)**: Wybitna okazja z wysoką marżą i niskim ryzykiem (ramka zielona).
- **Score 5–7 (`verdict: "OBSERWUJ"`)**: Ciekawa oferta warta obserwacji lub podjęcia negocjacji (ramka żółta).
- **Score 1–4 (`verdict: "ODRZUĆ"`)**: Nieopłacalny sprzęt, wysoka cena lub duże ryzyko usterki BGA/zalania.

---

## 🔔 Elastyczne Alerty Discord & Telegram

Powiadomienia na Discordzie wysyłane są dla każdej oferty, która otrzyma od AI **`deal_score >= 5`** (werdykt **OKAZJA** lub **OBSERWUJ**):
- **Zielony Embed**: Werdykt `OKAZJA [8-10/10]`
- **Żółty Embed**: Werdykt `OBSERWUJ [5-7/10]`
- Każde powiadomienie zawiera:
  - Werdykt i dokładną ocenę AI,
  - Cenę Vinted, szacowaną cenę rynkową oraz koszt części/naprawy,
  - Zysk na czysto (Net Profit) oraz ROI (%),
  - Zwięzłe uzasadnienie wygenerowane przez Qwena (`reasoning`),
  - Bezpośredni link do oferty.

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
