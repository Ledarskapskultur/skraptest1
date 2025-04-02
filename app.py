import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import datetime
import urllib.parse

st.set_page_config(page_title="UGL Kurser", page_icon="📅")
st.title("UGL Kurser – Datum och priser")

# SIDOPANEL: Kontaktuppgifter och filter
st.sidebar.header("Kontaktuppgifter")
namn = st.sidebar.text_input("Namn")
telefon = st.sidebar.text_input("Telefon")
mail = st.sidebar.text_input("Mail")

st.sidebar.header("Filter")
week_filter_input = st.sidebar.text_input("Vecka (t.ex. 15,7 eller 35-37)")
price_filter_input = st.sidebar.number_input("Max Pris (kr)", min_value=0, value=0, step=100)

st.sidebar.subheader("Restid")
user_location = st.sidebar.text_input("Plats (din plats)")
user_transport = st.sidebar.selectbox("Färdsätt", options=["Bil", "Kollektivt"])
user_restid = st.sidebar.number_input("Restid (timmar)", min_value=0, value=0, step=1)

# Hjälpfunktioner

def parse_week_filter(week_str):
    """Parsa veckofiltreringssträngen till en mängd heltal."""
    allowed = set()
    if not week_str.strip():
        return allowed
    parts = week_str.split(',')
    for part in parts:
        part = part.strip()
        if '-' in part:
            bounds = part.split('-')
            try:
                start = int(bounds[0])
                end = int(bounds[1])
                allowed.update(range(start, end+1))
            except:
                pass
        else:
            try:
                allowed.add(int(part))
            except:
                pass
    return allowed

def get_travel_time(user_city, mode):
    """Simulerad restid (i timmar) från en användarstad till Eskilstuna."""
    travel_times = {
        "Bil": {
            "Västerås": 1.0,
            "Kiruna": 6.0,
            "Eskilstuna": 0.0,
            "Stockholm": 1.5,
        },
        "Kollektivt": {
            "Västerås": 2.0,
            "Kiruna": 8.0,
            "Eskilstuna": 0.0,
            "Stockholm": 2.5,
        }
    }
    if mode in travel_times and user_city in travel_times[mode]:
        return travel_times[mode][user_city]
    else:
        return 99.0  # Om vi inte känner igen staden, antas restiden vara mycket lång

def extract_price(price_str):
    """Extrahera numeriskt värde ur prissträngen (t.ex. '26 300 kr')."""
    try:
        return int(re.sub(r'\D', '', price_str))
    except:
        return 0

def add_space_between_words(text):
    """Lägg in mellanslag där ihopklistrade ord förekommer (t.ex. 'PatriciaStahl')."""
    return re.sub(r'(?<=[a-zåäö])(?=[A-ZÅÄÖ])', ' ', text)

def shorten_year(datum):
    """
    Ändra årtal från 4-siffrigt till 2-siffrigt i datumsträngen.
    Exempel: "07 Apr - 11 Apr 2025" → "07 Apr - 11 Apr 25"
    """
    return re.sub(r'(\d{2} \w{3} - \d{2} \w{3} )\d{2}(\d{2})', r'\1\2', datum)

# Hämtning och tolkning av kursdata

URL = "https://www.uglkurser.se/datumochpriser.php"

@st.cache_data
def fetch_ugl_data():
    response = requests.get(URL)
    soup = BeautifulSoup(response.content, "html.parser")
    
    table = soup.find("table")
    rows = table.find_all("tr")[1:]  # Hoppa över header
    
    data = []
    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 4:
            # Kursdatum & Vecka
            kursdatum_rader = list(cols[0].stripped_strings)
            datum = kursdatum_rader[0] if len(kursdatum_rader) > 0 else ""
            datum = shorten_year(datum)
            vecka = kursdatum_rader[1].replace("Vecka", "").strip() if len(kursdatum_rader) > 1 else ""
            
            # Kursplats: Anläggning, Ort, Platser kvar
            kursplats_rader = list(cols[1].stripped_strings)
            anlaggning_och_ort = kursplats_rader[0] if len(kursplats_rader) > 0 else ""
            anlaggning_split = anlaggning_och_ort.split(",")
            anlaggning = anlaggning_split[0].strip()
            ort = anlaggning_split[1].strip() if len(anlaggning_split) > 1 else ""
            
            platser_kvar = ""
            if len(kursplats_rader) > 1 and "Platser kvar:" in kursplats_rader[1]:
                platser_kvar = kursplats_rader[1].split("Platser kvar:")[1].strip()
            
            # Kursledare
            kursledare_rader = list(cols[2].stripped_strings)
            kursledare1 = add_space_between_words(kursledare_rader[0]) if len(kursledare_rader) > 0 else ""
            kursledare2 = add_space_between_words(kursledare_rader[1]) if len(kursledare_rader) > 1 else ""
            
            # Pris
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

# Filtrering

week_filter_set = parse_week_filter(week_filter_input)
price_filter_value = int(price_filter_input) if price_filter_input else 0
restid_active = user_location.strip() != "" and user_restid > 0

filter_active = bool(week_filter_set or price_filter_value > 0 or restid_active)

filtered_df = df.copy()

if filter_active:
    # Veckofiltrering
    if week_filter_set:
        try:
            filtered_df = filtered_df[filtered_df["Vecka"].astype(int).isin(week_filter_set)]

