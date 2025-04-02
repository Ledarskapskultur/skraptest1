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
    rows = table.find_all("tr")[1:]  # Skippa headern

    data = []
    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 5:
            vecka = add_space_between_words(cols[0].get_text(strip=True))
            datum = add_space_between_words(cols[1].get_text(strip=True))
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
