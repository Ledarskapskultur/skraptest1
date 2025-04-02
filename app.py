import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import datetime
import re

st.title("Corecode – UGL-kurser i tabellform")

def fetch_corecode_data():
    """
    Hämtar data från:
    https://www.corecode.se/oppna-utbildningar/ugl-utbildning?showall=true&filterBookables=-1
    
    Returnerar en DataFrame med kolumnerna:
    [Vecka, Datum, Anläggning, Ort, Handledare]
    """
    url = "https://www.corecode.se/oppna-utbildningar/ugl-utbildning?showall=true&filterBookables=-1"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    # Hitta tabellen
    table = soup.find("table")
    if not table:
        return pd.DataFrame(columns=["Vecka", "Datum", "Anläggning", "Ort", "Handledare"])

    # Hämta rubriker
    headers = [th.get_text(strip=True) for th in table.find("tr").find_all("th")]
    # Ex: ["Startdatum", "Plats", "Handledare", "Platser kvar"]

    # Hämta rader
    rows_data = []
    for tr in table.find_all("tr")[1:]:
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if not cells:
            continue
        row_dict = dict(zip(headers, cells))
        
        # 1) Vecka + Datum
        startdatum = row_dict.get("Startdatum", "").strip()
        # Ex: "2025-04-07"
        vecka_str = ""
        datum_str = startdatum
        if re.match(r"^\d{4}-\d{2}-\d{2}$", startdatum):
            try:
                dt = datetime.datetime.strptime(startdatum, "%Y-%m-%d")
                # Vecka
                week_num = dt.isocalendar()[1]
                vecka_str = f"Vecka {week_num}"
                # Datum, t.ex. "7/4 25"
                datum_str = dt.strftime("%-d/%-m %y")  # OBS: funkar på Unix/mac. På Windows kan du behöva %#d/%#m
            except:
                pass
        
        # 2) Plats -> Anläggning, Ort
        # Ex: "Stockholm: Bommersvik"
        plats = row_dict.get("Plats", "").strip()
        anlaggning = plats
        ort = ""
        if ":" in plats:
            left, right = plats.split(":", 1)
            ort = left.strip()           # ex: "Stockholm"
            anlaggning = right.strip()   # ex: "Bommersvik"

        # 3) Handledare
        # Ex: "Anne-Lie Ahlqvist , Jörgen Dahlström"
        # Ta bort eventuella extra mellanslag
        handledare_raw = row_dict.get("Handledare", "").strip()
        # Ex: "Anne-Lie Ahlqvist , Jörgen Dahlström"
        # Dela med "," eller " och " om du vill. Men här sätter vi allt i en kolumn.
        handledare_clean = re.sub(r"\s*,\s*", " & ", handledare_raw)
        
        # Bygg rad
        row_data = {
            "Vecka": vecka_str,
            "Datum": datum_str,
            "Anläggning": anlaggning,
            "Ort": ort,
            "Handledare": handledare_clean
        }
        rows_data.append(row_data)

    return pd.DataFrame(rows_data, columns=["Vecka", "Datum", "Anläggning", "Ort", "Handledare"])

df_corecode = fetch_corecode_data()

st.subheader("Corecode – bearbetad tabell")
st.dataframe(df_corecode, use_container_width=True)

# Vill du se raw? Avkommentera:
# st.write(df_corecode)
