# app/fetchers.py

import aiohttp
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

from .utils import log_error


# ---------------------------------------------------------
#  PARSER XML /xml
# ---------------------------------------------------------

def parse_xml(xml_text: str, ip: str | None = None):
    """
    Parsuje XML zwracany przez urządzenie.
    Zwraca dict lub None jeśli wystąpi błąd.
    """
    try:
        root = ET.fromstring(xml_text)
    except Exception as e:
        target = ip or "unknown"
        log_error(target, f"parse_xml error: {e}")
        return None

    name = root.findtext("name", "-")
    temps = []
    humidity = None

    # pobranie temperatur i wilgotności
    for inp in root.findall("input"):
        for var in inp.findall("var"):
            v = var.findtext("v")
            u = var.findtext("u", "") or ""

            if not v:
                continue

            # temp C
            if "C" in u and len(temps) < 3:
                try:
                    temps.append(float(v))
                except Exception:
                    temps.append(None)

            # wilgotność
            elif "%" in u:
                try:
                    humidity = float(v)
                except Exception:
                    humidity = None

    # uzupełnij temperatury do 3 wartości
    while len(temps) < 3:
        temps.append(None)

    return {
        "name": name,
        "temps": temps,
        "humidity": humidity,
    }


# ---------------------------------------------------------
#  FETCH /xml (z użyciem stałej sesji)
# ---------------------------------------------------------

async def fetch_device(session: aiohttp.ClientSession, ip: str):
    """
    Pobiera dane z http://<ip>/xml i zwraca sparsowany wynik.
    Korzysta z SESJI przekazanej z Dashboard.
    """
    url = f"http://{ip}/xml"

    try:
        async with session.get(url, timeout=5) as r:
            if r.status != 200:
                log_error(ip, f"HTTP {r.status} (xml)")
                return None

            text = await r.text()
    except Exception as e:
        log_error(ip, f"http error (xml): {e}")
        return None

    return parse_xml(text, ip=ip)


# ---------------------------------------------------------
#  FETCH /info (z użyciem stałej sesji)
# ---------------------------------------------------------

async def fetch_device_info(session: aiohttp.ClientSession, ip: str):
    """
    Pobiera dane z http://<ip>/info i wyciąga MAC/SN/Model.
    Korzysta z SESJI przekazanej z Dashboard.
    """
    url = f"http://{ip}/info"

    try:
        async with session.get(url, timeout=5) as r:
            if r.status != 200:
                return None

            text = await r.text()
    except Exception:
        return None

    soup = BeautifulSoup(text, "html.parser")
    rows = soup.find_all("tr")

    mac = "-"
    sn = "-"
    model = "-"

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 2:
            continue

        key = cols[0].get_text(strip=True).replace(":", "").lower()
        val = cols[1].get_text(strip=True)

        # normalizacja kluczy z różnych wersji firmware
        if key in ("mac", "mac address"):
            mac = val

        elif key in ("serial number", "s/n", "sn"):
            sn = val

        elif key in ("device type", "model"):
            model = val

    return {"mac": mac, "sn": sn, "model": model}
