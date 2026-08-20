# Laptop Flipping Monitor (Vinted / OLX + Ollama LLM)

Skrypt w języku Python służący do automatycznego monitorowania nowych ogłoszeń laptopów na portalach **OLX.pl** oraz **Vinted.pl**. Wszelkie nowe ogłoszenia są przesyłane do lokalnego API **Ollama** z modelem **`qwen2.5:14b`**, który analizuje specyfikację, stan oraz cenę i wycenia opłacalność zakupu pod flipping (odsprzedaż z zyskiem).

W przypadku wykrycia przewidywanego zysku przekraczającego próg (domyślnie **> 150 PLN**), skrypt wysyła automatyczne powiadomienie na **Discord Webhook** oraz/lub **Bot Telegrama**.

---

## 🚀 Funkcje

- **Pobieranie ogłoszeń**: Automatyczne skanowanie portali OLX i Vinted pod kątem ofert laptopów.
- **Deduplikacja**: Pamięć podręczna w pliku `seen_listings.json` zabezpieczająca przed wielokrotnym ocenianiem tych samych ofert.
- **Wycena przez LLM (Ollama)**: Odpowiedzi z API Ollama w ścisłym formacie JSON zawierające:
  - `estimated_market_value`: Szacowaną wartość rynkową w PLN,
  - `estimated_profit`: Szacowany zysk netto w PLN,
  - `reasoning`: Analizę i uzasadnienie w języku polskim.
- **Powiadomienia**:
  - **Discord Webhook** (karty embed z nagłówkiem, ceną, szacowanym zyskiem, uzasadnieniem i miniaturką zdjęcia),
  - **Telegram Bot** (sformatowane wiadomości HTML).
- **Tryb CLI**: Wsparcie dla jednorazowego uruchomienia (`--once`) oraz testowania bez wywoływania API i webhooków (`--dry-run`).

---

## 🛠️ Wymagania i Instalacja

### 1. Wymagania systemowe
- Python 3.10+
- Zainstalowana i uruchomiona [Ollama](https://ollama.com/) z pobranym modelem `qwen2.5:14b`:
  ```bash
  ollama pull qwen2.5:14b
  ```

### 2. Instalacja zależności Python
```bash
pip install -r requirements.txt
```

---

## ⚙️ Konfiguracja

Aplikacja wykorzystuje zmienne środowiskowe do konfiguracji (`config.py`):

| Zmienna Środowiskowa | Domyślna Wartość | Opis |
|---|---|---|
| `OLLAMA_URL` | `http://localhost:11434` | Adres URL lokalnego serwera Ollama |
| `OLLAMA_MODEL` | `qwen2.5:14b` | Nazwa modelu LLM w Ollamie |
| `PROFIT_THRESHOLD_PLN` | `150.0` | Minimalny szacowany zysk kwalifikujący okazję |
| `DISCORD_WEBHOOK_URL` | `""` | URL Webhooka Discord do powiadomień |
| `TELEGRAM_BOT_TOKEN` | `""` | Token bota Telegram |
| `TELEGRAM_CHAT_ID` | `""` | ID czatu Telegram |
| `FETCH_INTERVAL_SECONDS` | `300` | Interwał sprawdzania ogłoszeń w sekundach |

---

## 💻 Uruchomienie

### 1. Praca ciągła (pętla co 5 minut)
```bash
python3 main.py
```

### 2. Jednorazowe sprawdzenie (`--once`)
```bash
python3 main.py --once
```

### 3. Tryb testowy / Dry-run (`--dry-run`)
Uruchamia pobieranie i mockuje wycenę oraz powiadomienia bez odpytywania Ollamy i wysyłania wiadomości:
```bash
python3 main.py --once --dry-run
```

---

## 🧪 Testy Jednostkowe

Uruchomienie zestawu testów `pytest`:
```bash
pytest
```
