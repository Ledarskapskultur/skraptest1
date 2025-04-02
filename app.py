import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import datetime
import urllib.parse
import random
import string

st.set_page_config(page_title="UGL Kurser", page_icon="📅")
st.title("UGL Kurser – Datum och priser")

# Funktion för att generera ett slumpmässigt ID (6 tecken, bokstäver + siffror)
def generate_random_id(length=6):
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choices(characters, k=length))

# Initiera ID i session_state om det inte finns
if "random_id" not in st.session_state:
    st.session_state.random_id = generate_random_id()

#############################
# SIDOPANEL: Kontaktuppgifter
#############################

st.sidebar.header("Kontaktuppgifter")
col_namn, col_tel = st.sidebar.columns(2)
namn = col_namn.text_input("Namn")
telefon = col_tel.text_input("Telefon")
mail = st.sidebar.text_input("Mail")
st.sidebar.text_input("ID", value=st.session_state.random_id, disabled=True)

#############################
# SIDOPANEL: Filter
#############################

st.sidebar.header("Filter")
col_vecka, col_pris = st.sidebar.columns(2)
week_filter_input = col_vecka.text_input("Vecka (t.ex. 15,7 eller 35-37)")
price_filter_input = col_pris.number_input("Max Pris (kr)", min_value=0, value=0, step=100)

st.sidebar.subheader("Restid")
user_location = st.sidebar.text_input("Plats (din plats)")
col_far, col_res = st.sidebar.columns(2)
user_transport = col_far.selectbox("Färdsätt", options=["Bil", "Kollektivt"])
user_restid = col_res.number_input("Restid (timmar)", min_value=0, value=0, step=1)

#############################
# Hjälpfunktioner
#############################

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
        "Bil": {"Västerås": 1.0, "Kiruna": 6.0, "Eskilstuna": 0.0, "Stockholm": 1.5},
        "Kollektivt": {"Västerås": 2.0, "Kiruna": 8.0, "Eskilstuna": 0.0, "Stockholm": 2.5},
    }
    if mode in travel_times and user_city in travel_times[mode]:
        return travel_times[mode][user_city]
    else:
        return 99.0

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

def format_course_date(datum):
    """
    Omvandlar t.ex. "12 Maj - 16 Maj 2025" till "12/5 - 16/5 25".
    Justeras efter önskemål.
    """
    month_mapping = {
        "Jan": "1", "Feb": "2", "Mar": "3", "Apr": "4", "Maj": "5",
        "Jun": "6", "Jul": "7", "Aug": "8", "Sep": "9", "Okt": "10",
        "Nov": "11", "Dec": "12"
    }
    pattern = r"(\d{1,2})\s+([A-Za-z]+)\s*-\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})"
    match = re.search(pattern, datum)
    if match:
        start_day = match.group(1)
        start_month = match.group(2)
        end_day = match.group(3)
        end_month = match.group(4)
        year = match.group(5)
        start_month_num = month_mapping.get(start_month, start_month)
        end_month_num = month_mapping.get(end_month, end_month)
        return f"{start_day}/{start_month_num} - {end_day}/{end_month_num} {year[-2:]}"
    else:
        return datum

def format_spots(spots):
    """
    Returnerar en HTML-sträng med en färgad ✅ beroende på antalet platser kvar.
    - Grönt om numeriskt värde >= 3
    - Orange om "Få" eller numeriskt < 3
    - Rött om "fullbokad" finns i texten
    Efter ikonen visas texten (i svart).
    """
    text = spots.strip()
    if "fullbokad" in text.lower():
        color = "red"
    elif "få" in text.lower():
        color = "orange"
    else:
        try:
            digits = re.sub(r"\D", "", text)
            if digits == "":
                color = "orange"
            else:
                num = int(digits)
                color = "green" if num >= 3 else "orange"
        except:
            color = "orange"
    return f'<span style="color: {color}; font-weight: bold;">✅</span> {text}'

#############################
# Hämtning av kursdata (från UGL-sidan)
#############################

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
        if len(cols) < 4:
            continue
        kursdatum_rader = list(cols[0].stripped_strings)
        datum = kursdatum_rader[0] if len(kursdatum_rader) > 0 else ""
        datum = format_course_date(datum)
        vecka = kursdatum_rader[1].replace("Vecka", "").strip() if len(kursdatum_rader) > 1 else ""
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
        kursledare2 = add_space_between_words(kursledare_rader[1]) if len(kursledare_rader) > 1 else ""
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

#############################
# Filtrering
#############################

week_filter_set = parse_week_filter(week_filter_input)
price_filter_value = int(price_filter_input) if price_filter_input else 0
restid_active = user_location.strip() != "" and user_restid > 0
filter_active = bool(week_filter_set or price_filter_value > 0 or restid_active)
filtered_df = df.copy()

if filter_active:
    if week_filter_set:
        try:
            filtered_df = filtered_df[filtered_df["Vecka"].astype(int).isin(week_filter_set)]
        except Exception as e:
            st.error("Fel vid filtrering av vecka: " + str(e))
    if price_filter_value > 0:
        filtered_df["PriceInt"] = filtered_df["Pris"].apply(extract_price)
        filtered_df = filtered_df[filtered_df["PriceInt"] <= (price_filter_value + 500)]
    if restid_active:
        def passes_restid(row):
            if row["Ort"].lower() == "eskilstuna":
                travel_time = get_travel_time(user_location.strip(), user_transport)
                return travel_time <= user_restid
            else:
                return True
        filtered_df = filtered_df[filtered_df.apply(passes_restid, axis=1)]
else:
    current_week = datetime.datetime.now().isocalendar()[1]
    allowed_weeks = {current_week + 1, current_week + 2}
    try:
        filtered_df = filtered_df[filtered_df["Vecka"].astype(int).isin(allowed_weeks)]
    except:
        pass

#############################
# Visa alla kurser i rader med 3 per rad
#############################

st.subheader("🔍 Välj kurser")
courses = list(filtered_df.iterrows())
selected_courses = []

for i in range(0, len(courses), 3):
    cols = st.columns(3)
    for j, (idx, row) in enumerate(courses[i:i+3]):
        with cols[j]:
            st.markdown("---")
            spots_html = format_spots(row["Platser kvar"])
            block = f"""
            <div style="margin-bottom: 1em;">
              <span style="white-space: nowrap;">
                📅 <strong>Vecka {row["Vecka"]}</strong> &nbsp; 
                <strong>{row["Datum"]}</strong>
              </span><br>
              🏨 <strong>{row["Anläggning"]}</strong><br>
              📍 <strong>{row["Ort"]}</strong><br>
              💰 <strong>{row["Pris"]}</strong> &nbsp; {spots_html}<br>
              👥 <strong>{row["Kursledare1"]}</strong><br>
              👥 <strong>{row["Kursledare2"]}</strong>
            </div>
            """
            st.markdown(block, unsafe_allow_html=True)
            if st.checkbox("Välj denna kurs", key=f"val_{idx}"):
                selected_courses.append(row)

if selected_courses:
    st.subheader("✅ Du har valt följande kurser:")
    st.dataframe(pd.DataFrame(selected_courses), use_container_width=True)

#############################
# Visa fullständig kurslista
#############################

if st.button("Visa Fullständig kurslista"):
    st.subheader("📋 Fullständig kurslista")
    st.dataframe(filtered_df, use_container_width=True)

#############################
# Skicka via mail med HTML
#############################

st.subheader("Skicka information om dina valda kurser")
if st.button("Skicka information via mail"):
    if selected_courses and mail.strip():
        # Hämta det aktuella slumpmässiga ID:t från session_state
        request_id = st.session_state.random_id
        # Efter att mailet skickats generera ett nytt ID
        st.session_state.random_id = generate_random_id()

        table_html = f"""
        Hej {namn},<br>
        Namn: {namn} &nbsp;&nbsp; Telefon: {telefon}<br>
        Mailadress: {mail}<br>
        Förfrågan ID: {request_id}<br><br>
        Här kommer dina valda kurser:<br><br>
        <table border="1" style="border-collapse: collapse;">
          <tr>
            <th>Vecka & Pris</th>
            <th>Datum</th>
            <th>Anläggning</th>
            <th>Ort</th>
          </tr>
        """
        for course in selected_courses:
            table_html += f"""
          <tr>
            <td>Vecka {course['Vecka']}<br>Pris: {course['Pris']}</td>
            <td>{course['Datum']}</td>
            <td>{course['Anläggning']}</td>
            <td>{course['Ort']}</td>
          </tr>
            """
        table_html += """
        </table>
        <br>
        Hälsningar,<br>
        Ditt Företag
        """
        table_html_single = table_html.replace("\n", "").replace("\r", "")
        subject = f"Valda kurser - Förfrågan ID: {request_id}"
        mailto_link = (
            f"mailto:{mail}"
            f"?subject={urllib.parse.quote(subject)}"
            f"&body={urllib.parse.quote(table_html_single)}"
        )
        st.markdown(
            f"**Klicka [här]({mailto_link}) för att skicka ett mail med dina valda kurser.**<br>"
            f"<em>OBS! Alla e-postklienter visar inte HTML korrekt.</em>",
            unsafe_allow_html=True
        )
    else:
        st.warning("Vänligen välj minst en kurs och ange din mailadress.")

#############################
# Skrapa och visa data från Rezon som en lista
#############################

st.subheader("Kurskategorier från Rezon")
@st.cache_data
def fetch_rezon_table():
    url = "https://rezon.se/kurskategorier/ugl/"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    table = soup.find("table")
    if table:
        headers = [th.get_text(strip=True) for th in table.find("tr").find_all("th")]
        rows = []
        for tr in table.find_all("tr")[1:]:
            cells = [td.get_text(strip=True) for td in tr.find_all("td")]
            if cells:
                row_dict = dict(zip(headers, cells))
                rows.append(row_dict)
        return rows
    else:
        return []

rezon_data = fetch_rezon_table()
if rezon_data:
    for row in rezon_data:
        st.markdown(f"- **Kurs:** {row.get('Kurs', '')} | **Kursdatum:** {row.get('Kursdatum', '')} | **Utbildningsort:** {row.get('Utbildningsort', '')} | **Handledare:** {row.get('Handledare', '')} | **Pris:** {row.get('Pris', '')} | **Bokningsdetaljer:** {row.get('Bokningsdetaljer', '')}")
else:
    st.write("Ingen tabell hittades på Rezon-sidan.")
