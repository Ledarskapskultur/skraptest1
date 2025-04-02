import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

st.set_page_config(page_title="UGL Kurser", page_icon="📅")
st.title("UGL Kurser – Datum och priser")

URL = "https://www.uglkurser.se/datumochpriser.php"

# Lägg till mellanslag mellan ihopklistrade ord
def add_space_between_words(text):
    return re.sub(r'(?<=[a-zåäö])(?=[A-ZÅÄÖ])', ' ', text)

@st.cache_data
def fetch_ugl_data():
    response = requests.get(URL)
    soup = BeautifulSoup(response.content, "html.parser")

    table = soup.find("table")
    rows = table.find_all("tr")[1:]  # Hoppa över tabellhuvudet

    data = []
    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 5:
            raw_vecka_datum = cols[0].get_text(strip=True)

            # Hämta datumintervall och vecka ur samma cell
            match_datum = re.search(r'\d{2} \w{3} - \d{2} \w{3} \d{4}', raw_vecka_datum)
            match_vecka = re.search(r'Vecka\s*\d+|\b\d{1,2}\b', raw_vecka_datum)

            datum = match_datum.group(0) if match_datum else ""
            vecka = match_vecka.group(0).replace("Vecka", "").strip() if match_vecka else ""

            ort = add_space_between_words(cols[2].get_text(strip=True))
            kursledare = add_space_between_words(cols[3].get_text(strip=True))
            pris = add_space_between_words(cols[4].get_text(strip=True))

            data.append({
                "Vecka": vecka,
                "Datum": datum,
                "Ort": ort,
                "Kursledare": kursledare,
                "Pris": pris
            })
    return pd.DataFrame(data)

df = fetch_ugl_data()

st.subheader("🔍 Förhandsvisning av de tre första kurserna")

for index, row in df.head(3).iterrows():
    st.markdown(f"""
    ---
    📅 **Vecka {row['Vecka']}**  
    📆 Datum: {row['Datum']}  
    📍 Ort: {row['Ort']}  
    👥 Kursledare: {row['Kursledare']}  
    💰 Pris: {row['Pris']}
    """)

st.subheader("📋 Fullständig kurslista")
st.dataframe(df, use_container_width=True)
