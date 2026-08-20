import os

# Ollama API settings
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:14b")

# Flipping evaluation threshold
PROFIT_THRESHOLD_PLN = float(os.getenv("PROFIT_THRESHOLD_PLN", "100.0"))
SHIPPING_COST_PLN = float(os.getenv("SHIPPING_COST_PLN", "15.0"))

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

# Multi-category electronics configuration with keywords and filters
CATEGORIES = {
    "Laptopy": {
        "keywords": ["laptop", "thinkpad", "dell latitude", "uszkodzony", "brak dysku"],
        "olx_url": "https://www.olx.pl/elektronika/komputery/laptopy/",
        "vinted_search": "laptop"
    },
    "Konsole": {
        "keywords": ["ps4", "xbox one", "switch", "nie czyta płyt", "głośno chodzi"],
        "olx_url": "https://www.olx.pl/elektronika/gry-konsole/",
        "vinted_search": "konsola"
    },
    "Karty graficzne": {
        "keywords": ["rtx", "gtx", "rx", "artefakty", "przegrzewa się"],
        "olx_url": "https://www.olx.pl/elektronika/komputery/czesci/karty-graficzne/",
        "vinted_search": "karta graficzna"
    },
    "Drukarki 3D": {
        "keywords": ["ender", "neptune", "zatkana", "brak serwa"],
        "olx_url": "https://www.olx.pl/elektronika/komputery/drukarki-skanery/",
        "vinted_search": "drukarka 3d"
    },
    "Sprzęt Audio": {
        "keywords": ["amplituner", "brak dźwięku", "trzeszczy", "uszkodzony kanał"],
        "olx_url": "https://www.olx.pl/elektronika/sprzet-audio/",
        "vinted_search": "amplituner"
    }
}
