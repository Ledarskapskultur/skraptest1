import requests
from bs4 import BeautifulSoup
import re
import urllib.parse

def skrapa_uglkurser_kurser():
    url = "https://www.uglkurser.se/datumochpriser.php"
    response = requests.get(url)
    if response.status_code != 200:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    tabell = soup.find("table", {"class": "ugltable"})
    if not tabell:
        return []

    rader = tabell.find_all("tr")[1:]
    kurser = []

    for rad in rader:
        kolumner = rad.find_all("td")
        if len(kolumner) < 6:
            continue

        try:
            datum = kolumner[0].get_text(strip=True)
            plats = kolumner[1].get_text(strip=True)
            handledare = kolumner[2].get_text(strip=True)
            pris = kolumner[3].get_text(strip=True)
            status = kolumner[4].get_text(strip=True)
            länk = kolumner[5].find("a")["href"] if kolumner[5].find("a") else url
            maps = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(plats)}"

            kurs = {
                "namn": f"UGL {datum}",
                "datum": datum,
                "plats": plats,
                "handledare": handledare,
                "pris": pris,
                "platser": status,
                "hemsida": länk,
                "maps": maps
            }

            kurser.append(kurs)
        except Exception:
            continue

    return kurser
