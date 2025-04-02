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

def shorten_year(datum):
    """
    Byt '2025' -> '25' om datumsträngen matchar "dd Mmm - dd Mmm yyyy".
    Exempel: "07 Apr - 11 Apr 2025" -> "07 Apr - 11 Apr 25"
    """
    return re.sub(r'(\d{2} \w{3} - \d{2} \w{3} )\d{2}(\d{2})', r'\1\2', datum)

@st.cache_data
def fetch_ugl_data():
    response = requests.get(URL)
    soup = BeautifulSoup(response.content, "html.parser")
    
    table = soup.find("table")
    rows = table.find_all("tr")[1:]  # Skippa headern
    
    data = []
    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 4:
            # === Kursdatum & Vecka ===
            kursdatum_rader = list(cols[0].stripped_strings)
            datum = kursdatum_rader[0] if len(kursdatum_rader) > 0 else ""
            datum = shorten_year(datum)  # Gör om årtalet till två siffror
            vecka = kursdatum_rader[1].replace("Vecka", "").strip() if len(kursdatum_rader) > 1 else ""
            
            # === Kursplats: Anläggning, Ort, Platser kvar ===
            kursplats_rader = list(cols[1].stripped_strings)
            anlaggning_och_ort = kursplats_rader[0] if len(kursplats_rader) > 0 else ""
            anlaggning_split = anlaggning_och_ort.split(",")
            anlaggning = anlaggning_split[0].strip()
            ort = anlaggning_split[1].strip() if len(anlaggning_split) > 1 else ""
            
            platser_kvar = ""
            if len(kursplats_rader) > 1 and "Platser kvar:" in kursplats_rader[1]:
                platser_kvar = kursplats_rader[1].split("Platser kvar:")[1].strip()
            
            # === Kursledare (två separata) ===
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

st.subheader("🔍 Välj kurser")

# Visa kurser i 3 kolumner (3 per rad, totalt 9 kurser visas här; ändra .head(n) om du vill fler)
cols = st.columns(3)
selected_courses = []

for i, row in df.head(9).iterrows():
    col = cols[i % 3]
    with col:
        st.markdown("---")
        # Använd HTML med white-space: nowrap för att hindra radbrytning av årtal
        st.markdown(
            f"""
            <div style="margin-bottom: 1em;">
              <span style="white-space: nowrap;">
                📅 <strong>Vecka {row['Vecka']}</strong> &nbsp; 📆 <strong>{row['Datum']}</strong>
              </span><br>
              🏨 <strong>{row['Anläggning']}</strong><br>
              📍 <strong>{row['Ort']}</strong><br>
              💰 <strong>{row['Pris']}</strong> &nbsp; ✅ <strong>Platser kvar: {row['Platser kvar']}</strong><br>
              👥 <strong>{row['Kursledare1']}</strong><br>
              👥 <strong>{row['Kursledare2']}</strong>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.checkbox("Välj denna kurs", key=f"val_{i}"):
            selected_courses.append(row)

if selected_courses:
    st.subheader("✅ Du har valt följande kurser:")
    st.dataframe(pd.DataFrame(selected_courses), use_container_width=True)

st.subheader("📋 Fullständig kurslista")
st.dataframe(df, use_container_width=True)
