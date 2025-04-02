import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

st.set_page_config(page_title="UGL Kurser", page_icon="📅")
st.title("UGL Kurser – Datum och priser")

URL = "https://www.uglkurser.se/datumochpriser.php"

def add_space_between_words(text):
    return re.sub(r'(?<=[a-zåäö])(?=[A-ZÅÄÖ])', ' ', text)

@st.cache_data
def fetch_ugl_data():
    response = requests.get(URL)
    soup = BeautifulSoup(response.content, "html.parser")

    table = soup.find("table")
    rows = table.find_all("tr")[1:]

    data = []
    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 4:
            # === Kursdatum ===
            kursdatum_rader = list(cols[0].stripped_strings)
            datum = kursdatum_rader[0] if len(kursdatum_rader) > 0 else ""
            vecka = kursdatum_rader[1].replace("Vecka", "").strip() if len(kursdatum_rader) > 1 else ""

            # === Kursplats ===
            kursplats_rader = list(cols[1].stripped_strings)
            anlaggning_och_ort = kursplats_rader[0] if len(kursplats_rader) > 0 else ""
            anlaggning_split = anlaggning_och_ort.split(",")
            anlaggning = anlaggning_split[0].strip()
            ort = anlaggning_split[1].strip() if len(anlaggning_split) > 1 else ""

            platser_kvar = ""
            if len(kursplats_rader) > 1 and "Platser kvar:" in kursplats_rader[1]:
                platser_kvar = kursplats_rader[1].split("Platser kvar:")[1].strip()

            # === Kursledare ===
            kursledare_rader = list(cols[2].stripped_strings)
            kursledare1 = add_space_between_words(kursledare_rader[0]) if len(kursledare_rader) > 0 else ""
            kursledare2 = add_space_between_words(kursledare_rader[1]) if len(kursledare_rader) > 1 else ""

            # === Pris ===
            pris_rader = list(cols[3].stripped_strings)
            pris = pris_rader[0] if len(pris_rader) > 0 else ""

            data.append({
                "Vecka": vecka,
                "Datum": datum,
                "Anläggning": anlaggning,
                "Ort": ort,
                "Platser kvar": platser_kvar,
                "Kursledare1": kursledare1,
                "Kursledare2": kursledare2,
                "Pris": pris
            })

    return pd.DataFrame(data)

df = fetch_ugl_data()

st.subheader("🔍 Förhandsvisning av de tre första kurserna")

col1, col2 = st.columns(2)

for i, row in df.head(3).iterrows():
    target_col = col1 if i % 2 == 0 else col2
    with target_col:
        st.markdown(f"""
        ---
        📅 **Vecka {row['Vecka']}**   📆 **Datum: {row['Datum']}**  
        🏨 **Anläggning: {row['Anläggning']}**   📍 **Ort: {row['Ort']}**  
        💰 **Pris: {row['Pris']}**   ✅ **Platser kvar: {row['Platser kvar']}**  
        👥 **Kursledare: {row['Kursledare1']} och {row['Kursledare2']}**
        """)

st.subheader("📋 Fullständig kurslista")
st.dataframe(df, use_container_width=True)
