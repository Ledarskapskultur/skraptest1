import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import datetime
import urllib.parse
import random
import string

# Sätt upp sidans titel och ikon
st.set_page_config(page_title="UGL Kurser", page_icon="📅")
st.title("UGL Kurser – Datum och priser")

####################################
# Funktioner för slumpmässigt ID
####################################
def generate_random_id(length=6):
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choices(characters, k=length))

if "random_id" not in st.session_state:
    st.session_state.random_id = generate_random_id()

####################################
# SIDOPANEL: Kontaktuppgifter
####################################
st.sidebar.header("Kontaktuppgifter")
col_namn, col_tel = st.sidebar.columns(2)
namn = col_namn.text_input("Namn")
telefon = col_tel.text_input("Telefon")
mail = st.sidebar.text_input("Mail")
st.sidebar.text_input("ID", value=st.session_state.random_id, disabled=True)

####################################
# SIDOPANEL: Filter
####################################
st.sidebar.header("Filter")
col_v, col_pris = st.sidebar.columns(2)
week_filter_input = col_v.text_input("V (t.ex. 7,15 eller 35-37)")
price_filter_input = col_pris.number_input("Max Pris (kr)", min_value=0, value=0, step=100)

st.sidebar.subheader("Restid")
user_location = st.sidebar.text_input("Plats (din plats)")
col_far, col_res = st.sidebar.columns(2)
user_transport = col_far.selectbox("Färdsätt", options=["Bil", "Kollektivt"])
user_restid = col_res.number_input("Restid (timmar)", min_value=0, value=0, step=1)

####################################
# Hjälpfunktioner för UGL-data
####################################
def parse_week_filter(week_str):
    allowed = set()
    if not week_str.strip():
        return allowed
    parts = week_str.split(',')
    for part in parts:
        part = part.strip()
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
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
    return travel_times.get(mode, {}).get(user_city, 99.0)

def extract_price(price_str):
    try:
        return int(re.sub(r'\D', '', price_str))
    except:
        return 0

def add_space_between_words(text):
    return re.sub(r'(?<=[a-zåäö])(?=[A-ZÅÄÖ])', ' ', text)

def shorten_year(datum):
    return re.sub(r'(\d{2} \w{3} - \d{2} \w{3} )\d{2}(\d{2})', r'\1\2', datum)

# Konverterar datum från formatet "YYYY-MM-DD - YYYY-MM-DD" till "DD/M - DD/M YY"
def format_course_date(datum):
    parts = datum.split(" - ")
    if len(parts) == 2:
        try:
            s_year, s_month, s_day = parts[0].split("-")
            e_year, e_month, e_day = parts[1].split("-")
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

####################################
# Hämta UGL-data
####################################
UGL_URL = "https://www.uglkurser.se/datumochpriser.php"

@st.cache_data
def fetch_ugl_data():
    response = requests.get(UGL_URL)
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
        vecka = f"📅 Vecka {vecka}"
        kursplats_rader = list(cols[1].stripped_strings)
        anlaggning_och_ort = kursplats_rader[0] if len(kursplats_rader) > 0 else ""
        anlaggning_split = anlaggning_och_ort.split(",")
        anlaggning = anlaggning_split[0].strip()
        ort = anlaggning_split[1].strip() if len(anlaggning_split) > 1 else ""
        platser_kvar = ""
        if len(kursplats_rader) > 1 and "Platser kvar:" in kursplats_rader[1]:
            platser_kvar = kursplats_rader[1].split("Platser kvar:")[1].strip()
        kursledare_rader = list(cols[2].stripped_strings)
        handledare1 = add_space_between_words(kursledare_rader[0]) if len(kursledare_rader) > 0 else ""
        handledare2 = add_space_between_words(kursledare_rader[1]) if len(kursledare_rader) > 1 else ""
        pris_rader = list(cols[3].stripped_strings)
        pris = pris_rader[0] if len(pris_rader) > 0 else ""
        data.append({
            "Vecka": vecka,
            "Datum": datum,
            "Anläggning": anlaggning,
            "Ort": ort,
            "Handledare1": handledare1,
            "Handledare2": handledare2,
            "Pris": pris,
            "Platser kvar": platser_kvar,
            "Källa": "UGL"
        })
    return pd.DataFrame(data)

ugl_df = fetch_ugl_data()

####################################
# Processa Rezon-data
####################################
def process_rezon_row(row_dict):
    kursdatum = row_dict.get("Kursdatum", "")
    if "Vecka" in kursdatum:
        date_part, week_part = kursdatum.split("Vecka", 1)
        date_part = date_part.strip()   # ex: "2025-04-07 - 2025-04-11"
        week_part = week_part.strip()     # ex: "15"
    else:
        date_part = kursdatum.strip()
        week_part = ""
    def transform_date(d):
        parts = d.split(" - ")
        if len(parts)==2:
            try:
                s = parts[0].split("-")
                e = parts[1].split("-")
                return f"{int(s[2])}/{int(s[1])} - {int(e[2])}/{int(e[1])} {s[0][-2:]}"
            except:
                return d
        else:
            return d
    new_date = transform_date(date_part)
    new_week = f"📅 Vecka {week_part}" if week_part else ""
    utbildningsort = row_dict.get("Utbildningsort", "")
    if "Tylebäck" in utbildningsort:
        new_anlaggning = "🏨 Sundbyholms Slott"
        new_ort = "📍 Eskilstuna"
    else:
        utd = add_space_between_words(utbildningsort)
        parts = utd.split()
        new_anlaggning = parts[0] if parts else utd
        new_ort = " ".join(parts[1:]) if len(parts) > 1 else ""
    handledare = row_dict.get("Handledare", "")
    def split_handledare(text):
        m = re.findall(r'[A-ZÅÄÖ][^A-ZÅÄÖ]+', text)
        if len(m) >= 2:
            return m[0].strip(), m[1].strip()
        else:
            parts = text.split()
            if len(parts) >= 2:
                return parts[0], parts[1]
            else:
                return text, ""
    new_handledare1, new_handledare2 = split_handledare(add_space_between_words(handledare))
    pris_text = row_dict.get("Pris", "")
    prices = re.findall(r'(\d[\d\s]*)\s*kr', pris_text)
    total_price = 0
    for p in prices:
        try:
            total_price += int(p.replace(" ", ""))
        except:
            pass
    new_pris = f"{total_price} kr"
    bokningsdetaljer = row_dict.get("Bokningsdetaljer", "")
    new_platser = "Få" if "fullbokad" in bokningsdetaljer.lower() else bokningsdetaljer
    return {
        "Vecka": new_week,
        "Datum": new_date,
        "Anläggning": new_anlaggning,
        "Ort": new_ort,
        "Handledare1": new_handledare1,
        "Handledare2": new_handledare2,
        "Pris": new_pris,
        "Platser kvar": new_platser,
        "Källa": "Rezon"
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
            # Ignorera om kursnamnet innehåller "UGL - Utveckling av grupp och ledare"
            kurs_namn = row_dict.get("Kurs", "")
            if "UGL - Utveckling av grupp och ledare" in kurs_namn:
                pass
            else:
                rows.append(processed)
    return rows

rezon_data = fetch_rezon_data()
rezon_df = pd.DataFrame(rezon_data)

####################################
# Kombinera UGL- och Rezon-data
####################################
if not rezon_df.empty:
    combined_df = pd.concat([ugl_df, rezon_df], ignore_index=True)
else:
    combined_df = ugl_df.copy()

####################################
# Filtrering på kombinerad data
####################################
week_filter_set = parse_week_filter(week_filter_input)
price_filter_value = int(price_filter_input) if price_filter_input else 0
restid_active = user_location.strip() != "" and user_restid > 0
filtered_df = combined_df.copy()

if week_filter_set:
    try:
        filtered_df["WeekInt"] = filtered_df["Vecka"].str.replace("📅 Vecka", "").str.strip().apply(lambda x: int(x) if x.isdigit() else None)
        filtered_df = filtered_df.dropna(subset=["WeekInt"])
        filtered_df = filtered_df[filtered_df["WeekInt"].isin(week_filter_set)]
    except Exception as e:
        st.error("Fel vid filtrering av V: " + str(e))
if price_filter_value > 0:
    filtered_df["PriceInt"] = filtered_df["Pris"].apply(extract_price)
    filtered_df = filtered_df[filtered_df["PriceInt"] <= (price_filter_value + 500)]
if restid_active:
    def passes_restid(row):
        ort = row["Ort"].replace("📍", "").strip().lower()
        if ort == "eskilstuna":
            travel_time = get_travel_time(user_location.strip(), user_transport)
            return travel_time <= user_restid
        else:
            return True
    filtered_df = filtered_df[filtered_df.apply(passes_restid, axis=1)]

if not (week_filter_set or price_filter_value > 0 or restid_active):
    current_week = datetime.datetime.now().isocalendar()[1]
    allowed_weeks = {current_week + 1, current_week + 2}
    try:
        filtered_df["WeekInt"] = filtered_df["Vecka"].str.replace("📅 Vecka", "").str.strip().apply(lambda x: int(x) if x.isdigit() else None)
        filtered_df = filtered_df.dropna(subset=["WeekInt"])
        filtered_df = filtered_df[filtered_df["WeekInt"].isin(allowed_weeks)]
    except:
        pass

####################################
# Visa kurser i 3 kolumner (kombinerad data)
####################################
st.subheader("🔍 Välj kurser (UGL + Rezon)")
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
                {row["Vecka"]} &nbsp; <strong>{row["Datum"]}</strong>
              </span><br>
              🏨 <strong>{row["Anläggning"]}</strong><br>
              📍 <strong>{row["Ort"]}</strong><br>
              💰 <strong>{row["Pris"]}</strong> &nbsp; {spots_html}<br>
              👥 <strong>{row["Handledare1"]}</strong><br>
              👥 <strong>{row["Handledare2"]}</strong><br>
              <em>Källa: {row.get("Källa", "")}</em>
            </div>
            """
            st.markdown(block, unsafe_allow_html=True)
            if st.checkbox("Välj denna kurs", key=f"val_{idx}"):
                selected_courses.append(row)

if selected_courses:
    st.subheader("✅ Du har valt följande kurser:")
    st.dataframe(pd.DataFrame(selected_courses), use_container_width=True)

####################################
# Visa fullständig kurslista
####################################
if st.button("Visa Fullständig kurslista"):
    st.subheader("📋 Fullständig kurslista")
    st.dataframe(filtered_df, use_container_width=True)

####################################
# Skicka via mail med HTML (kombinerad data)
####################################
st.subheader("Skicka information om dina valda kurser")
if st.button("Skicka information via mail"):
    if selected_courses and mail.strip():
        request_id = st.session_state.random_id
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
            <td>{course['Vecka']}<br>Pris: {course['Pris']}</td>
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

####################################
# Visa rådata från Rezon (som lista)
####################################
st.subheader("Rådata från Rezon (skrapad och processad)")
@st.cache_data
def fetch_rezon_table_data():
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

rezon_list = fetch_rezon_table_data()
if rezon_list:
    for r in rezon_list:
        st.markdown(f"- **Datum:** {r['Datum']}, {r['Vecka']}, **Anläggning:** {r['Anläggning']}, **Ort:** {r['Ort']}, **Handledare:** {r['Handledare1']} / {r['Handledare2']}, **Pris:** {r['Pris']}, **Platser kvar:** {r['Platser kvar']}, **Källa:** {r.get('Källa', '')}")
else:
    st.write("Ingen data hittades från Rezon.")
