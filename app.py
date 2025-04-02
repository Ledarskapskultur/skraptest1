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

# ----- Hjälpfunktioner -----

def parse_week_filter(week_str):
    # Parsar en textsträng (t.ex. "15,7" eller "35-37") till en mängd heltal.
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
                allowed.update(range(start, end + 1))
            except:
                pass
        else:
            try:
                allowed.add(int(part))
            except:
                pass
    return allowed

def get_travel_time(user_city, mode):
    # Returnerar restid i timmar från en ort till Eskilstuna, enligt en enkel hårdkodad tabell.
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
        return 99.0

def extract_price(price_str):
    # Tar ut siffrorna ur en prissträng, t.ex. "26 300 kr" -> 26300.
    try:
        return int(re.sub(r"\D", "", price_str))
    except:
        return 0

def add_space_between_words(text):
    # Infogar mellanslag mellan liten bokstav och stor bokstav.
    return re.sub(r'(?<=[a-zåäö])(?=[A-ZÅÄÖ])', ' ', text)

def shorten_year(datum):
    # Byter "2025" mot "25" i strängar som "07 Apr - 11 Apr 2025".
    return re.sub(r'(\d{2} \w{3} - \d{2} \w{3} )\d{2}(\d{2})', r'\1\2', datum)

# ----- Hämtning och tolkning av kursdata -----

URL = "https://www.uglkurser.se/datumochpriser.php"

@st.cache_data
def fetch_ugl_data():
    response = requests.get(URL)
    soup = BeautifulSoup(response.content, "html.parser")
    
    table = soup.find("table")
    rows = table.find_all("tr")[1:]
    
    data = []
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 4:
            continue
        
        kursdatum_rader = list(cols[0].stripped_strings)
        datum = kursdatum_rader[0] if len(kursdatum_rader) > 0 else ""
        datum = shorten_year(datum)
        vecka = ""
        if len(kursdatum_rader) > 1:
            vecka = kursdatum_rader[1].replace("Vecka", "").strip()
        
        kursplats_rader = list(cols[1].stripped_strings)
        anlaggning_och_ort = kursplats_rader[0] if len(kursplats_rader) > 0 else ""
        anlaggning_split = anlaggning_och_ort.split(",")
        anlaggning = anlaggning_split[0].strip()
        ort = anlaggning_split[1].strip() if len(anlaggning_split) > 1 else ""
        
        platser_kvar = ""
        if len(kursplats_rader) > 1 and "Platser kvar:" in kursplats_rader[1]:
            platser_kvar = kursplats_rader[1].split("Platser kvar:")[1].strip()
        
        kursledare_rader = list(cols[2].stripped_strings)
        kursledare1 = add_space_between_words(kursledare_rader[0]) if len(kursledare_rader) > 0 else ""
        kursledare2 = ""
        if len(kursledare_rader) > 1:
            kursledare2 = add_space_between_words(kursledare_rader[1])
        
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

# ----- Filtrering -----

week_filter_set = parse_week_filter(week_filter_input)
price_filter_value = int(price_filter_input) if price_filter_input else 0
restid_active = (user_location.strip() != "" and user_restid > 0)

filter_active = bool(week_filter_set or price_filter_value > 0 or restid_active)
filtered_df = df.copy()

if filter_active:
    # Filtrera på vecka
    if week_filter_set:
        try:
            filtered_df = filtered_df[filtered_df["Vecka"].astype(int).isin(week_filter_set)]
        except Exception as e:
            st.error("Fel vid filtrering av vecka: " + str(e))
    
    # Filtrera på pris (kurspris <= maxpris + 500)
    if price_filter_value > 0:
        filtered_df["PriceInt"] = filtered_df["Pris"].apply(extract_price)
        filtered_df = filtered_df[filtered_df["PriceInt"] <= (price_filter_value + 500)]
    
    # Filtrera på restid (endast Ort "Eskilstuna")
    if restid_active:
        def passes_restid(row):
            if row["Ort"].lower() == "eskilstuna":
                travel_time = get_travel_time(user_location.strip(), user_transport)
                return travel_time <= user_restid
            else:
                return True
        filtered_df = filtered_df[filtered_df.apply(passes_restid, axis=1)]
else:
    # Om inga filter -> visa kommande 2 veckors kurser
    current_week = datetime.datetime.now().isocalendar()[1]
    allowed_weeks = {current_week + 1, current_week + 2}
    try:
        filtered_df = filtered_df[filtered_df["Vecka"].astype(int).isin(allowed_weeks)]
    except:
        pass

# ----- Visa kurser i 3 kolumner -----

st.subheader("Välj kurser")

cols = st.columns(3)
selected_courses = []

for i, row in filtered_df.head(9).iterrows():
    col = cols[i % 3]
    with col:
        st.markdown("---")
        block = f"""
        <div style="margin-bottom: 1em;">
          <span style="white-space: nowrap;">
            📅 <strong>Vecka {row["Vecka"]}</strong> &nbsp; 
            📆 <strong>{row["Datum"]}</strong>
          </span><br>
          🏨 <strong>{row["Anläggning"]}</strong><br>
          📍 <strong>{row["Ort"]}</strong><br>
          💰 <strong>{row["Pris"]}</strong> &nbsp; 
          ✅ <strong>Platser kvar: {row["Platser kvar"]}</strong><br>
          👥 <strong>{row["Kursledare1"]}</strong><br>
          👥 <strong>{row["Kursledare2"]}</strong>
        </div>
        """
        st.markdown(block, unsafe_allow_html=True)
        
        if st.checkbox("Välj denna kurs", key=f"val_{i}"):
            selected_courses.append(row)

if selected_courses:
    st.subheader("Du har valt följande kurser:")
    st.dataframe(pd.DataFrame(selected_courses), use_container_width=True)

# Knapp för fullständig lista
if st.button("Visa Fullständig kurslista"):
    st.subheader("Fullständig kurslista")
    st.dataframe(filtered_df, use_container_width=True)

# Skicka info via mail (HTML-tabell)
st.subheader("Skicka information om dina valda kurser")
if st.button("Skicka information via mail"):
    if selected_courses and mail.strip():
        table_html = """
        <table border="1" style="border-collapse: collapse;">
          <tr>
            <th>Vecka</th>
            <th>Datum</th>
            <th>Anläggning</th>
            <th>Ort</th>
            <th>Pris</th>
          </tr>
        """
        for course in selected_courses:
            table_html += f"""
            <tr>
              <td>{course['Vecka']}</td>
              <td>{course['Datum']}</td>
              <td>{course['Anläggning']}</td>
              <td>{course['Ort']}</td>
              <td>{course['Pris']}</td>
            </tr>
            """
        table_html += "</table>"
        
        subject = "Valda kurser"
        mailto_link = f"mailto:{mail}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(table_html)}"
        st.markdown(
            f"Klicka [här]({mailto_link}) för att skicka ett mail med dina valda kurser.<br>"
            f"<em>OBS! Alla e-postklienter visar inte HTML korrekt.</em>",
            unsafe_allow_html=True
        )
    else:
        st.warning("Vänligen välj minst en kurs och ange din mailadress.")
