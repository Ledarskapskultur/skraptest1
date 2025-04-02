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
    """Ex: "7,15 eller 35-37" -> set av int."""
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
        "Bil": {
            "Västerås": 1.0, "Kiruna": 6.0,
            "Eskilstuna": 0.0, "Stockholm": 1.5
        },
        "Kollektivt": {
            "Västerås": 2.0, "Kiruna": 8.0,
            "Eskilstuna": 0.0, "Stockholm": 2.5
        }
    }
    return travel_times.get(mode, {}).get(user_city, 99.0)

def extract_price(price_str):
    try:
        return int(re.sub(r'\D', '', price_str))
    except:
        return 0

def add_space_between_words(text):
    # Infoga mellanslag där stor bokstav följer en liten bokstav
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

# Konvertera datum "YYYY-MM-DD - YYYY-MM-DD" -> "DD/M - DD/M YY"
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
        # Datum & Vecka
        kursdatum_rader = list(cols[0].stripped_strings)
        datum = kursdatum_rader[0] if kursdatum_rader else ""
        datum = format_course_date(datum)
        vecka = kursdatum_rader[1].replace("Vecka", "").strip() if len(kursdatum_rader) > 1 else ""
        vecka = f"📅 Vecka {vecka}"

        # Plats
        kursplats_rader = list(cols[1].stripped_strings)
        anlaggning_och_ort = kursplats_rader[0] if kursplats_rader else ""
        anlaggning_split = anlaggning_och_ort.split(",")
        anlaggning = anlaggning_split[0].strip()
        ort = anlaggning_split[1].strip() if len(anlaggning_split) > 1 else ""

        # Platser kvar
        platser_kvar = ""
        if len(kursplats_rader) > 1 and "Platser kvar:" in kursplats_rader[1]:
            platser_kvar = kursplats_rader[1].split("Platser kvar:")[1].strip()

        # Handledare
        kursledare_rader = list(cols[2].stripped_strings)
        handledare1 = add_space_between_words(kursledare_rader[0]) if kursledare_rader else ""
        handledare2 = add_space_between_words(kursledare_rader[1]) if len(kursledare_rader) > 1 else ""

        # Pris
        pris_rader = list(cols[3].stripped_strings)
        pris = pris_rader[0] if pris_rader else ""

        data.append({
            "Vecka": vecka,
            "Datum": datum,
            "Anläggning": anlaggning,
            "Ort": ort,
            "Handledare1": handledare1,
            "Handledare2": handledare2,
            "Pris": pris,
            "Platser kvar": platser_kvar,
            "Källa": "uglkurser"  # <-- Här sätter vi källan
        })
    return pd.DataFrame(data)

####################################
# 6) Hämta Rezon-data
####################################
def process_rezon_row(row_dict):
    kursdatum = row_dict.get("Kursdatum", "")
    # T.ex. "2025-04-07 - 2025-04-11Vecka 15"
    week_part = ""
    date_part = kursdatum.strip()
    if "Vecka" in kursdatum:
        parts = kursdatum.split("Vecka", 1)
        date_part = parts[0].strip()
        week_part = parts[1].strip()

    # Datum
    def transform_date(d):
        pr = d.split(" - ")
        if len(pr) == 2:
            try:
                sy, sm, sd = pr[0].split("-")
                ey, em, ed = pr[1].split("-")
                return f"{int(sd)}/{int(sm)} - {int(ed)}/{int(em)} {sy[-2:]}"
            except:
                return d
        else:
            return d

    new_date = transform_date(date_part)
    new_week = f"📅 Vecka {week_part}" if week_part else ""

    # Utbildningsort
    utbildningsort = row_dict.get("Utbildningsort", "")
    if "Tylebäck" in utbildningsort:
        new_anlaggning = "🏨 Sundbyholms Slott"
        new_ort = "📍 Eskilstuna"
    else:
        utd = add_space_between_words(utbildningsort)
        parts = utd.split()
        new_anlaggning = parts[0] if parts else utd
        new_ort = " ".join(parts[1:]) if len(parts) > 1 else ""

    # Handledare
    handledare = row_dict.get("Handledare", "")
    def split_handledare(text):
        # Försök hitta två segment med stor bokstav
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

    # Pris (summera)
    pris_text = row_dict.get("Pris", "")
    prices = re.findall(r'(\d[\d\s]*)\s*kr', pris_text)
    total = 0
    for p in prices:
        try:
            total += int(p.replace(" ", ""))
        except:
            pass
    new_pris = f"{total} kr"

    # Platser kvar
    boknings = row_dict.get("Bokningsdetaljer", "")
    new_spots = "Få" if "fullbokad" in boknings.lower() else boknings

    return {
        "Vecka": new_week,
        "Datum": new_date,
        "Anläggning": new_anlaggning,
        "Ort": new_ort,
        "Handledare1": h1,
        "Handledare2": h2,
        "Pris": new_pris,
        "Platser kvar": new_spots,
        "Källa": "rezon"  # <-- Här sätter vi källan
    }

def fetch_rezon_data():
    url = "https://rezon.se/kurskategorier/ugl/"
    resp = requests.get(url)
    soup = BeautifulSoup(resp.content, "html.parser")
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
            # Kursnamn
            kurs_namn = row_dict.get("Kurs", "")
            # Om du vill ignorera rader som har "UGL - Utveckling av grupp och ledare" i fältet "Kurs" - ta bort eller ändra
            if "UGL - Utveckling av grupp och ledare" in kurs_namn:
                pass
            else:
                rows.append(processed)
    return rows

####################################
# 7) Kombinera data & filtrera
####################################
ugl_df = fetch_ugl_data()
rezon_rows = fetch_rezon_data()
rezon_df = pd.DataFrame(rezon_rows)

if not rezon_df.empty:
    combined_df = pd.concat([ugl_df, rezon_df], ignore_index=True)
else:
    combined_df = ugl_df.copy()

# Filtrering
week_filter_set = parse_week_filter(week_filter_input)
price_filter_value = int(price_filter_input) if price_filter_input else 0
restid_active = user_location.strip() != "" and user_restid > 0
filtered_df = combined_df.copy()

if week_filter_set:
    try:
        # Konvertera "📅 Vecka 15" -> 15
        def safe_week_int(v):
            w = v.replace("📅 Vecka", "").strip()
            return int(w) if w.isdigit() else None

        filtered_df["WeekInt"] = filtered_df["Vecka"].apply(safe_week_int)
        filtered_df = filtered_df.dropna(subset=["WeekInt"])
        filtered_df = filtered_df[filtered_df["WeekInt"].isin(week_filter_set)]
    except Exception as e:
        st.error("Fel vid filtrering av V: " + str(e))

if price_filter_value > 0:
    filtered_df["PriceInt"] = filtered_df["Pris"].apply(extract_price)
    filtered_df = filtered_df[filtered_df["PriceInt"] <= (price_filter_value + 500)]

if restid_active:
    def passes_restid(row):
        # Om orten är "📍 Eskilstuna", kolla travel_time
        ort = row["Ort"].replace("📍", "").strip().lower()
        if ort == "eskilstuna":
            travel_time = get_travel_time(user_location.strip(), user_transport)
            return travel_time <= user_restid
        else:
            return True
    filtered_df = filtered_df[filtered_df.apply(passes_restid, axis=1)]

# Om inga filter är aktiva -> visa kommande 2 veckors kurser
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
# 8) Visa i 3 kolumner
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
            # Ex: Källa: uglkurser eller rezon
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
              Källa: <em>{row["Källa"]}</em>
            </div>
            """
            st.markdown(block, unsafe_allow_html=True)
            if st.checkbox("Välj denna kurs", key=f"val_{idx}"):
                selected_courses.append(row)

if selected_courses:
    st.subheader("✅ Du har valt följande kurser:")
    st.dataframe(pd.DataFrame(selected_courses), use_container_width=True)

####################################
# 9) Visa fullständig kurslista
####################################
if st.button("Visa Fullständig kurslista"):
    st.subheader("📋 Fullständig kurslista")
    st.dataframe(filtered_df, use_container_width=True)

####################################
# 10) Skicka via mail
####################################
st.subheader("Skicka information om dina valda kurser")
if st.button("Skicka information via mail"):
    if selected_courses and mail.strip():
        # Hämta slump-ID
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
