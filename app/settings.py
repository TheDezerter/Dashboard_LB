# app/settings.py

import os
import json
from datetime import datetime, timedelta

# ---------------------------------------------------------
#  ŚCIEŻKI DO KATALOGÓW
# ---------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data")
HISTORY_DIR = os.path.join(DATA_DIR, "history")
LOGS_DIR = os.path.join(DATA_DIR, "logs")

ALERTS_FILE = os.path.join(DATA_DIR, "alerts.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

# upewniamy się, że katalogi istnieją
for d in (DATA_DIR, HISTORY_DIR, LOGS_DIR):
    os.makedirs(d, exist_ok=True)


# ---------------------------------------------------------
#  DOMYŚLNE USTAWIENIA GLOBALNE
# ---------------------------------------------------------

DEFAULT_SETTINGS = {
    "refresh_interval": 10,      # sekundy
    "history_days": 10,          # ile dni przechowujemy dane
    "temp_min": 10.0,
    "temp_max": 25.0,
    "hum_min": 20.0,
    "hum_max": 80.0,
    "panels_per_row": 5          # ile paneli w jednym rzędzie
}


# ---------------------------------------------------------
#  ZAPIS / ODCZYT USTAWIEŃ
# ---------------------------------------------------------

def save_settings(data: dict):
    """Zapis ustawień do pliku JSON."""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception:
        pass  # nie wyłączamy aplikacji w razie błędu I/O


def load_settings():
    """
    Wczytuje ustawienia globalne.
    Braki są automatycznie uzupełniane wartościami domyślnymi.
    """
    if not os.path.exists(SETTINGS_FILE):
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        # jeśli plik uszkodzony
        return DEFAULT_SETTINGS.copy()

    # uzupełnianie brakujących kluczy
    updated = False
    for key, val in DEFAULT_SETTINGS.items():
        if key not in data:
            data[key] = val
            updated = True

    if updated:
        save_settings(data)

    return data


# globalne ustawienia — wczytywane raz
SETTINGS = load_settings()


# ---------------------------------------------------------
#  POMOCNICZE
# ---------------------------------------------------------

def history_cutoff_date():
    """Zwraca graniczną datę dla czyszczenia historii na podstawie ustawień."""
    days = SETTINGS.get("history_days", DEFAULT_SETTINGS["history_days"])
    return datetime.now() - timedelta(days=days)
