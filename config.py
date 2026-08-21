import os

# Ollama API settings (allows MODEL_NAME or OLLAMA_MODEL environment variable, defaults to qwen2.5:7b)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("MODEL_NAME", os.getenv("OLLAMA_MODEL", "qwen2.5:7b"))

# Optional Proxy settings for scrapers (e.g. "http://user:pass@host:port" or "socks5://host:port")
PROXY_URL = os.getenv("PROXY_URL", "")

# Flipping & Repair evaluation thresholds
PROFIT_THRESHOLD_FLIP_PLN = float(os.getenv("PROFIT_THRESHOLD_FLIP_PLN", "80.0"))
PROFIT_THRESHOLD_REPAIR_PLN = float(os.getenv("PROFIT_THRESHOLD_REPAIR_PLN", "100.0"))
SHIPPING_COST_PLN = float(os.getenv("SHIPPING_COST_PLN", "20.0"))

# Webhook / Notification settings
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Scraper settings
FETCH_INTERVAL_SECONDS = int(os.getenv("FETCH_INTERVAL_SECONDS", "300"))
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
}

# Cache file path for seen listings
SEEN_CACHE_FILE = os.getenv("SEEN_CACHE_FILE", "seen_listings.json")

# Pre-filtering keywords for fault/damage detection (case-insensitive)
FAULT_KEYWORDS = [
    "uszkodz",
    "zepsut",
    "nietest",
    "dawc",
    "napraw",
    "brak",
    "wada",
    "wadliw",
    "pękn",
    "zalaw",
    "zalani",
    "restart",
    "nie włącza",
    "nie wlacz",
    "nie dziala",
    "nie działa",
    "rozbit",
    "spalon",
    "hasło",
    "bios",
    "artefakt",
    "skaza",
    "część",
    "stan"
]

# Pre-filtering exclusion keywords for laptop spare parts / components
EXCLUDE_PARTS = [
    "ram",
    "procesor",
    "processzorok",
    "cpu",
    "dysk",
    "ssd",
    "hdd",
    "matryca",
    "płyta główna",
    "plyta glowna",
    "obudowa",
    "klawiatura do",
    "bateria do"
]

# Pre-filtering exclusion keywords for toys and children items
EXCLUDE_TOYS = [
    "zabawka",
    "zabawkowy",
    "edukacyjny",
    "dla dzieci",
    "hello kitty",
    "barbie",
    "fisher price",
    "interaktywny",
    "grający",
    "minnie",
    "paws",
    "psi patrol"
]

# Multi-category electronics configuration with raised max_price limits and cheap auto-pass thresholds
CATEGORIES = {
    "Laptopy": {
        "max_price": 1200.0,
        "cheap_threshold": 250.0,
        "keywords": ["laptop", "thinkpad", "dell latitude", "uszkodzony", "brak dysku"],
        "olx_url": "https://www.olx.pl/elektronika/komputery/laptopy/",
        "vinted_search": "laptop"
    },
    "Konsole": {
        "max_price": 900.0,
        "cheap_threshold": 150.0,
        "keywords": ["ps4", "xbox one", "switch", "nie czyta płyt", "głośno chodzi"],
        "olx_url": "https://www.olx.pl/elektronika/gry-konsole/",
        "vinted_search": "konsola"
    },
    "Karty graficzne": {
        "max_price": 1000.0,
        "cheap_threshold": 150.0,
        "keywords": ["rtx", "gtx", "rx", "artefakty", "przegrzewa się"],
        "olx_url": "https://www.olx.pl/elektronika/komputery/czesci/karty-graficzne/",
        "vinted_search": "karta graficzna"
    },
    "Drukarki 3D": {
        "max_price": 800.0,
        "cheap_threshold": 200.0,
        "keywords": ["ender", "neptune", "zatkana", "brak serwa"],
        "olx_url": "https://www.olx.pl/elektronika/komputery/drukarki-skanery/",
        "vinted_search": "drukarka 3d"
    },
    "Sprzęt Audio": {
        "max_price": 600.0,
        "cheap_threshold": 150.0,
        "keywords": ["amplituner", "brak dźwięku", "trzeszczy", "uszkodzony kanał"],
        "olx_url": "https://www.olx.pl/elektronika/sprzet-audio/",
        "vinted_search": "amplituner"
    }
}
