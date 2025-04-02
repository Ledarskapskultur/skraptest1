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

####################################
# 1) Slumpmässigt ID
####################################
def generate_random_id(length=6):
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=length))

if "random_id" not in st.session_state:
    st.session_state.random_id = generate_random_id()

####################################
# 2) SIDOPANEL: Kontaktuppgifter
####################################
st.sidebar.header("Kontaktuppgifter")
col_namn, col_tel = st.sidebar.columns(2)
namn = col_namn.text_input("Namn")
telefon = col_tel.text_input("Telefon")
mail = st.sidebar.text_input("Mail")
st.sidebar.text_input("ID", value=st.session_state.random_id, disabled=True)

####################################
# 3) SIDOPANEL: Filter
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
# 4) Hjälpfunktioner
####################################
def parse_week_filter(week_str):
    """Ex: '7,15 eller 35-37' -> set av int."""
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
    # Infoga mellanslag där en liten bokstav följs av en stor bokstav.
    return re.sub(r'(?<=[a-zåäö])(?=[A-ZÅÄÖ])', ' ', text)

def format_spots(spots):
    text = spots.strip()
    if "fullbokad" in text.lower():
        color = "red"
    elif "få" in text.lower():
        color = "orange"
    else:
        try:
            digits = re.sub(r"\D", "", text)
            num = int(digits) if digits else 0
            color = "green" if num >= 3 else "orange"
        except:
            color = "orange"
    return f'<span style="color: {color}; font-weight: bold;">✅</span> {text}'

def format_course_date(datum):
    # Omvandlar "YYYY-MM-DD - YYYY-MM-DD" till "DD/M - DD/M YY"
    parts = datum.split(" - ")
    if len(parts) == 2:
        try:
            s_year, s_month, s_day = parts[0].split("-")
            e_year, e_month, e_day = parts[1].split("-")
            return f"{int(s_day)}/{int(s_month)} - {int(e_day)}/{int(e_month)} {s_year[-2:]}"
        except:
            return datum
    return datum

def combine_handledare(h1, h2):
    if h1 and h2:
        return f"{h1} {h2}"
    else:
        return h1 or h2

####################################
# 5) Hämta UGL-data
####################################
UGL_URL = "https://www.uglkurser.se/datumochpriser.php"

def fetch_ugl_data():
    resp = requests.get(UGL_URL)
    soup = BeautifulSoup(resp.content, "html.parser")
    table = soup.find("table")
    rows = table.find_all("tr")[1:]
    data = []
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 4:
            continue
        kursdatum_rader = list(cols[0].stripped_strings)
        datum = kursdatum_rader[0] if kursdatum_rader else ""
        datum = format_course_date(datum)
        vecka = kursdatum_rader[1].replace("Vecka", "").strip() if len(kursdatum_rader) > 1 else ""
        vecka = f"📅 Vecka {vecka}"
        kursplats_rader = list(cols[1].stripped_strings)
        anlaggning_och_ort = kursplats_rader[0] if kursplats_rader else ""
        splitted = anlaggning_och_ort.split(",")
        anlaggning = splitted[0].strip()
        ort = splitted[1].strip() if len(splitted) > 1 else ""
        platser_kvar = ""
        if len(kursplats_rader) > 1 and "Platser kvar:" in kursplats_rader[1]:
            platser_kvar = kursplats_rader[1].split("Platser kvar:")[1].strip()
        kursledare_rader = list(cols[2].stripped_strings)
        h1 = add_space_between_words(kursledare_rader[0]) if kursledare_rader else ""
        h2 = add_space_between_words(kursledare_rader[1]) if len(kursledare_rader)>1 else ""
        handledare = combine_handledare(h1, h2)
        pris_rader = list(cols[3].stripped_strings)
        pris = pris_rader[0] if pris_rader else ""
        data.append({
            "Vecka": vecka,
            "Datum": datum,
            "Anläggning": anlaggning,
            "Ort": ort,
            "Handledare": handledare,
            "Pris": pris,
            "Platser kvar": platser_kvar,
            "Källa": "Uglkurser"
        })
    return pd.DataFrame(data)

ugl_df = fetch_ugl_data()

####################################
# 6) Hämta Rezon-data
####################################
def process_rezon_row(row_dict):
    kursdatum = row_dict.get("Kursdatum", "")
    week_part = ""
    date_part = kursdatum.strip()
    if "Vecka" in kursdatum:
        parts = kursdatum.split("Vecka", 1)
        date_part = parts[0].strip()
        week_part = parts[1].strip()
    new_date = format_course_date(date_part)
    new_week = f"📅 Vecka {week_part}" if week_part else ""
    utbildningsort = row_dict.get("Utbildningsort", "")
    if "Tylebäck" in utbildningsort:
        new_anlaggning = "🏨 Sundbyholms Slott"
        new_ort = "📍 Eskilstuna"
    else:
        utd = add_space_between_words(utbildningsort)
        parts = utd.split()
        new_anlaggning = parts[0] if parts else utd
        new_ort = " ".join(parts[1:]) if len(parts)>1 else ""
    handledare = row_dict.get("Handledare", "")
    def split_handledare(text):
        m = re.findall(r'[A-ZÅÄÖ][^A-ZÅÄÖ]+', text)
        if len(m) >= 2:
            return m[0].strip(), m[1].strip()
        else:
            sp = text.split()
            if len(sp) >= 2:
                return sp[0], " ".join(sp[1:])
            else:
                return text, ""
    h1, h2 = split_handledare(add_space_between_words(handledare))
    handledare_combined = combine_handledare(h1, h2)
    pris_text = row_dict.get("Pris", "")
    prices = re.findall(r'(\d[\d\s]*)\s*kr', pris_text)
    total_price = 0
    for p in prices:
        try:
            total_price += int(p.replace(" ", ""))
        except:
            pass
    new_pris = f"{total_price} kr"
    boknings = row_dict.get("Bokningsdetaljer", "")
    new_spots = "Få" if "fullbokad" in boknings.lower() else boknings
    return {
        "Vecka": new_week,
        "Datum": new_date,
        "Anläggning": new_anlaggning,
        "Ort": new_ort,
        "Handledare": handledare_combined,
        "Pris": new_pris,
        "Platser kvar": new_spots,
        "Källa": "Rezon"
    }

def fetch_rezon_data():
    rez_url = "https://rezon.se/kurskategorier/ugl/"
    resp = requests.get(rez_url)
    soup = BeautifulSoup(resp.content, "html.parser")
    table = soup.find("table")
    if not table:
        return []
    headers = [th.get_text(strip=True) for th in table.find("tr").find_all("th")]
    rows_data = []
    for tr in table.find_all("tr")[1:]:
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if cells:
            row_dict = dict(zip(headers, cells))
            processed = process_rezon_row(row_dict)
            rows_data.append(processed)
    return rows_data

rezon_list = fetch_rezon_data()
rezon_df = pd.DataFrame(rezon_list)

####################################
# 7) Hämta Corecode-data
####################################
def fetch_corecode_data():
    corecode_url = "https://www.corecode.se/oppna-utbildningar/ugl-utbildning?showall=true&filterBookables=-1"
    resp = requests.get(corecode_url)
    soup = BeautifulSoup(resp.content, "html.parser")
    table = soup.find("table")
    if not table:
        return []
    headers = [th.get_text(strip=True) for th in table.find("tr").find_all("th")]
    rows_data = []
    for tr in table.find_all("tr")[1:]:
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if cells:
            row_dict = dict(zip(headers, cells))
            # För Corecode, kolumner: "Startdatum", "Plats", "Handledare", "Platser kvar"
            startdatum = row_dict.get("Startdatum", "")
            try:
                dt = datetime.datetime.strptime(startdatum, "%Y-%m-%d")
                datum_formatted = dt.strftime("%-d/%-m %y")  # Använder %-d och %-m (på Unix; på Windows kan du behöva %#d/%#m %y)
                week_num = dt.isocalendar()[1]
                vecka = f"📅 Vecka {week_num}"
            except Exception as e:
                datum_formatted = startdatum
                vecka = ""
            plats = row_dict.get("Plats", "")
            if ":" in plats:
                anlaggning, ort = [s.strip() for s in plats.split(":", 1)]
            else:
                anlaggning = plats
                ort = ""
            handledare = row_dict.get("Handledare", "")
            handledare = add_space_between_words(handledare)
            # Låt handledare visas på en rad (om det är två, behåll mellanslaget)
            platser = row_dict.get("Platser kvar", "")
            try:
                platser_int = int(platser)
                platser_out = "Få" if platser_int == 0 else platser
            except:
                platser_out = platser
            rows_data.append({
                "Vecka": vecka,
                "Datum": datum_formatted,
                "Anläggning": anlaggning,
                "Ort": ort,
                "Handledare": handledare,
                "Pris": row_dict.get("Pris", ""),
                "Platser kvar": platser_out,
                "Källa": "Corecode"
            })
    return rows_data

corecode_list = fetch_corecode_data()
corecode_df = pd.DataFrame(corecode_list)

####################################
# 8) Kombinera data & Filtrering
####################################
# Kombinera UGL, Rezon och Corecode-data
combined_df = pd.concat([ugl_df, rezon_df, corecode_df], ignore_index=True)

week_filter_set = parse_week_filter(week_filter_input)
price_filter_value = int(price_filter_input)
restid_active = user_location.strip() != "" and user_restid > 0
filtered_df = combined_df.copy()

if week_filter_set:
    try:
        def safe_week_int(v):
            w = v.replace("📅 Vecka", "").strip()
            return int(w) if w.isdigit() else None
        filtered_df["WeekInt"] = filtered_df["Vecka"].apply(safe_week_int)
        filtered_df = filtered_df.dropna(subset=["WeekInt"])
        filtered_df = filtered_df[filtered_df["WeekInt"].isin(week_filter_set)]
    except Exception as e:
        st.error(f"Fel vid filtrering av V: {e}")
if price_filter_value > 0:
    filtered_df["PriceInt"] = filtered_df["Pris"].apply(extract_price)
    filtered_df = filtered_df[filtered_df["PriceInt"] <= (price_filter_value + 500)]
if restid_active:
    def passes_restid(row):
        ort = row["Ort"].replace("📍", "").strip().lower()
        if ort == "eskilstuna":
            travel_time = get_travel_time(user_location.strip(), user_transport)
            return travel_time <= user_restid
        return True
    filtered_df = filtered_df[filtered_df.apply(passes_restid, axis=1)]

if not (week_filter_set or price_filter_value or restid_active):
    current_week = datetime.datetime.now().isocalendar()[1]
    allowed_weeks = {current_week + 1, current_week + 2}
    def safe_week_int(v):
        w = v.replace("📅 Vecka", "").strip()
        return int(w) if w.isdigit() else None
    filtered_df["WeekInt"] = filtered_df["Vecka"].apply(safe_week_int)
    filtered_df = filtered_df.dropna(subset=["WeekInt"])
    filtered_df = filtered_df[filtered_df["WeekInt"].isin(allowed_weeks)]

####################################
# 9) Visa i 3 kolumner (kombinerad data)
####################################
st.subheader("🔍 Välj kurser (Kombinerad)")
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
              <span style="white-space: nowrap;">{row["Vecka"]} &nbsp; <strong>{row["Datum"]}</strong></span><br>
              🏨 <strong>{row["Anläggning"]}</strong><br>
              📍 <strong>{row["Ort"]}</strong><br>
              💰 <strong>{row["Pris"]}</strong> &nbsp; {spots_html}<br>
              👥 <strong>{row["Handledare"]}</strong><br>
              {row["Källa"]}
            </div>
            """
            st.markdown(block, unsafe_allow_html=True)
            if st.checkbox("Välj denna kurs", key=f"val_{idx}"):
                selected_courses.append(row)

if selected_courses:
    st.subheader("✅ Du har valt följande kurser:")
    st.dataframe(pd.DataFrame(selected_courses), use_container_width=True)

####################################
# 10) Visa fullständig kurslista
####################################
if st.button("Visa Fullständig kurslista"):
    st.subheader("📋 Fullständig kurslista")
    st.dataframe(filtered_df, use_container_width=True)

####################################
# 11) Skicka via mail med HTML
####################################
st.subheader("Skicka information om dina valda kurser")
if st.button("Skicka information via mail"):
    if selected_courses and mail.strip():
        req_id = st.session_state.random_id
        st.session_state.random_id = generate_random_id()
        table_html = f"""
        Hej {namn},<br>
        Namn: {namn} &nbsp;&nbsp; Telefon: {telefon}<br>
        Mailadress: {mail}<br>
        Förfrågan ID: {req_id}<br><br>
        Här kommer dina valda kurser:<br><br>
        <table border="1" style="border-collapse: collapse;">
          <tr>
            <th>Vecka & Pris</th>
            <th>Datum</th>
            <th>Anläggning</th>
            <th>Ort</th>
            <th>Källa</th>
          </tr>
        """
        for course in selected_courses:
            table_html += f"""
          <tr>
            <td>{course['Vecka']}<br>Pris: {course['Pris']}</td>
            <td>{course['Datum']}</td>
            <td>{course['Anläggning']}</td>
            <td>{course['Ort']}</td>
            <td>{course['Källa']}</td>
          </tr>
            """
        table_html += """
        </table>
        <br>
        Hälsningar,<br>
        Ditt Företag
        """
        table_html_single = table_html.replace("\n", "").replace("\r", "")
        subject = f"Valda kurser - Förfrågan ID: {req_id}"
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
# 12) Visa Corecode-data som lista (samma plats som övriga resultat)
####################################
st.subheader("Corecode-data (skrapad)")
corecode_list = fetch_corecode_data()
if corecode_list:
    for r in corecode_list:
        st.markdown(f"- {r['Vecka']} {r['Datum']}, {r['Anläggning']}, {r['Ort']}, {r['Handledare']}, {r['Pris']}, {r['Platser kvar']}, {r['Källa']}")
else:
    st.write("Ingen Corecode-data hittades.")
