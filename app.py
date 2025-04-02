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

# Funktion för att generera ett slumpmässigt ID (6 tecken: bokstäver + siffror)
def generate_random_id(length=6):
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choices(characters, k=length))

# Initiera slumpmässigt ID i session_state om det inte finns
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
# Hjälpfunktioner (för UGL-data)
#############################
def parse_week_filter(week_str):
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
    travel_times = {
        "Bil": {"Västerås": 1.0, "Kiruna": 6.0, "Eskilstuna": 0.0, "Stockholm": 1.5},
        "Kollektivt": {"Västerås": 2.0, "Kiruna": 8.0, "Eskilstuna": 0.0, "Stockholm": 2.5},
    }
    if mode in travel_times and user_city in travel_times[mode]:
        return travel_times[mode][user_city]
    else:
        return 99.0

def extract_price(price_str):
    try:
        return int(re.sub(r'\D', '', price_str))
    except:
        return 0

def add_space_between_words(text):
    return re.sub(r'(?<=[a-zåäö])(?=[A-ZÅÄÖ])', ' ', text)

def shorten_year(datum):
    return re.sub(r'(\d{2} \w{3} - \d{2} \w{3} )\d{2}(\d{2})', r'\1\2', datum)

def format_course_date(datum):
    # Omvandlar t.ex. "2025-04-07 - 2025-04-11" till "07/4 - 11/4 25"
    parts = datum.split(" - ")
    if len(parts) == 2:
        try:
            start_date = parts[0].strip()
            end_date = parts[1].strip()
            s_year, s_month, s_day = start_date.split("-")
            e_year, e_month, e_day = end_date.split("-")
            return f"{int(s_day)}/{int(s_month)} - {int(e_day)}/{int(e_month)} {s_year[-2:]}"
        except:
            return datum
    else:
        return datum

def format_spots(spots):
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
# Hämtning av UGL-data
#############################
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
# Visa UGL-kurser (alla) i rader med 3 per rad
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
        # Hämta det aktuella slumpmässiga ID:t
        request_id = st.session_state.random_id
        # Efter att mailet skickats, generera ett nytt ID
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
# SKRAPA OCH BEHANDLA DATA FRÅN REZON
#############################
def process_rezon_row(row_dict):
    # Ignorera kursnamnet (ta bort "Kurs:" fältet)
    # Hantera Kursdatum: t.ex. "2025-04-07 - 2025-04-11Vecka 15"
    kursdatum = row_dict.get("Kursdatum", "")
    if "Vecka" in kursdatum:
        date_part, week_part = kursdatum.split("Vecka", 1)
        date_part = date_part.strip()  # t.ex. "2025-04-07 - 2025-04-11"
        week_part = week_part.strip()  # t.ex. "15"
    else:
        date_part = kursdatum.strip()
        week_part = ""
    # Transformera datumformat
    def transform_date(d):
        date_range = d.split(" - ")
        if len(date_range) == 2:
            try:
                s_year, s_month, s_day = date_range[0].split("-")
                e_year, e_month, e_day = date_range[1].split("-")
                return f"{int(s_day)}/{int(s_month)} - {int(e_day)}/{int(e_month)} {s_year[-2:]}"
            except:
                return d
        else:
            return d
    new_date = transform_date(date_part)
    new_week = f"📅 Vecka {week_part}" if week_part else ""
    # Utbildningsort: om texten är "TylebäckHalmstad" så sätt fasta värden
    utbildningsort = row_dict.get("Utbildningsort", "")
    if "Tylebäck" in utbildningsort:
        new_anlaggning = "🏨 Sundbyholms Slott"
        new_ort = "📍 Eskilstuna"
    else:
        # Annars använd add_space_between_words och försök dela upp vid första mellanslaget
        utd = add_space_between_words(utbildningsort)
        parts = utd.split()
        new_anlaggning = parts[0] if parts else utd
        new_ort = " ".join(parts[1:]) if len(parts) > 1 else ""
    # Handledare: dela upp i två
    handledare = row_dict.get("Handledare", "")
    def split_handledare(text):
        m = re.match(r"^([A-ZÅÄÖ][a-zåäö\s]+)([A-ZÅÄÖ].+)$", text)
        if m:
            return m.group(1).strip(), m.group(2).strip()
        else:
            parts = text.split()
            if len(parts) >= 2:
                return " ".join(parts[:-1]), parts[-1]
            else:
                return text, ""
    new_handledare1, new_handledare2 = split_handledare(add_space_between_words(handledare))
    # Pris: summera de två prisdelarna
    pris_text = row_dict.get("Pris", "")
    prices = re.findall(r"(\d[\d\s]*)\s*kr", pris_text)
    total_price = 0
    for p in prices:
        try:
            total_price += int(p.replace(" ", ""))
        except:
            pass
    new_pris = f"{total_price} kr"
    # Bokningsdetaljer: om det är "Fullbokad", sätt antalet lediga platser till "Få"
    bokningsdetaljer = row_dict.get("Bokningsdetaljer", "")
    new_platser = "Få" if "fullbokad" in bokningsdetaljer.lower() else bokningsdetaljer
    return {
        "Datum": new_date,
        "Vecka": new_week,
        "Anläggning": new_anlaggning,
        "Ort": new_ort,
        "Handledare1": new_handledare1,
        "Handledare2": new_handledare2,
        "Pris": new_pris,
        "Platser kvar": new_platser
    }

@st.cache_data
def fetch_rezon_data():
    url = "https://rezon.se/kurskategorier/ugl/"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    table = soup.find("table")
    if not table:
        return []
    headers = [th.get_text(strip=True) for th in table.find("tr").find_all("th")]
    rows = []
    for tr in table.find_all("tr")[1:]:
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if cells:
            row_dict = dict(zip(headers, cells))
            processed = process_rezon_row(row_dict)
            rows.append(processed)
    return rows

rezon_rows = fetch_rezon_data()

st.subheader("Data från Rezon")
if rezon_rows:
    for r in rezon_rows:
        st.markdown(
            f"- **Datum:** {r['Datum']}, **{r['Vecka']}**, **Anläggning:** {r['Anläggning']}, **Ort:** {r['Ort']}, **Handledare:** {r['Handledare1']} / {r['Handledare2']}, **Pris:** {r['Pris']}, **Platser kvar:** {r['Platser kvar']}"
        )
else:
    st.write("Ingen data hittades från Rezon.")
