# app/utils.py

import os
import json
from datetime import datetime

from .settings import HISTORY_DIR, LOGS_DIR, ALERTS_FILE, history_cutoff_date


MAX_ALERTS = 1000  # maksymalna liczba alertów w alerts.json


# ---------------------------------------------------------
#  PLIKI HISTORII
# ---------------------------------------------------------

def _device_file(ip: str) -> str:
    """
    Zwraca ścieżkę do pliku historii danego urządzenia.
    IP zamieniane na bezpieczną nazwę pliku.
    """
    safe = ip.replace(":", "_").replace(".", "_")
    return os.path.join(HISTORY_DIR, f"{safe}.json")


def load_device_history(ip: str) -> dict:
    """
    Wczytuje historię urządzenia.
    Zwraca zawsze poprawną strukturę słownika.
    """
    path = _device_file(ip)

    if not os.path.exists(path):
        return {"time": [], "t1": [], "t2": [], "t3": [], "hum": []}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        # reset na wypadek uszkodzonego pliku
        return {"time": [], "t1": [], "t2": [], "t3": [], "hum": []}

    # uzupełnienie brakujących kluczy
    for key in ["time", "t1", "t2", "t3", "hum"]:
        data.setdefault(key, [])

    return data


def save_device_history(ip: str, history: dict) -> None:
    """
    Zapisuje historię urządzenia.
    Aby zmniejszyć I/O — sprawdzamy czy dane się zmieniły.
    """
    path = _device_file(ip)

    try:
        # wczytujemy poprzednią zawartość
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                old = json.load(f)
        else:
            old = {}
    except Exception:
        old = {}

    # jeśli dane takie same — nie zapisujemy
    if old == history:
        return

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log_error(ip, f"save_device_history error: {e}")


def trim_history_days(history: dict) -> None:
    """
    Usuwa dane starsze niż graniczna data wyliczona z ustawień globalnych.
    """
    cutoff = history_cutoff_date()

    while history["time"]:
        try:
            t = datetime.fromisoformat(history["time"][0])
        except Exception:
            break

        if t >= cutoff:
            break

        # usuń najstarszy wpis
        for key in ["time", "t1", "t2", "t3", "hum"]:
            if history[key]:
                history[key].pop(0)


# ---------------------------------------------------------
#  ALERTY
# ---------------------------------------------------------

def load_alerts() -> list:
    if not os.path.exists(ALERTS_FILE):
        return []
    try:
        with open(ALERTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_alerts(alerts: list) -> None:
    """
    Zapis alertów z zachowaniem limitu MAX_ALERTS.
    """
    if len(alerts) > MAX_ALERTS:
        alerts = alerts[-MAX_ALERTS:]

    try:
        with open(ALERTS_FILE, "w", encoding="utf-8") as f:
            json.dump(alerts, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log_error("alerts", f"save_alerts error: {e}")


def log_alert(ip: str, message: str) -> None:
    """
    Dodaje nowy alert do pliku alerts.json.
    """
    try:
        alerts = load_alerts()
        alerts.append({
            "time": datetime.now().isoformat(),
            "ip": ip,
            "msg": message,
        })
        save_alerts(alerts)
    except Exception as e:
        log_error(ip, f"log_alert error: {e}")


# ---------------------------------------------------------
#  LOGOWANIE BŁĘDÓW
# ---------------------------------------------------------

def log_error(ip: str, msg: str) -> None:
    """
    Zapis błędów do dziennego pliku logów.
    Nie przerywa działania aplikacji.
    """
    now = datetime.now().strftime("%Y-%m-%d")
    logfile = os.path.join(LOGS_DIR, f"errors_{now}.log")

    try:
        with open(logfile, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat()}] {ip}: {msg}\n")
    except Exception:
        # nie wywalaj aplikacji z powodu błędu logowania
        pass
