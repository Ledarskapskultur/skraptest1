import streamlit as st
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

def generera_html_mail(kurser, namn):
    rows = ""
    for k in kurser:
        rows += f"""
        <tr>
            <td>{k.namn}</td>
            <td>{k.datum}</td>
            <td>{k.plats}</td>
            <td>{k.pris}</td>
            <td>{k.platser}</td>
            <td><a href="{k.hemsida}">Webbplats</a></td>
            <td><a href="{k.maps}">Karta</a></td>
        </tr>
        """
    html = f"""
    <html>
    <body>
    <h2>Hej {namn},</h2>
    <p>Här är de UGL-kurser du visat intresse för:</p>
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse;">
        <tr style="background-color:#f2f2f2;">
            <th>Kurs</th><th>Datum</th><th>Plats</th><th>Pris</th><th>Platstillgång</th><th>Hemsida</th><th>Karta</th>
        </tr>
        {rows}
    </table>
    <br>
    <p>Hör gärna av dig om du har frågor eller vill boka.</p>
    <p>Med vänliga hälsningar,<br>Ditt Kursbokningsteam</p>
    </body>
    </html>
    """
    return html

def skicka_mail(till, html_body, ämne="Din kursöversikt – UGL"):
    från = st.secrets["email"]["from_address"]
    lösenord = st.secrets["email"]["app_password"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = ämne
    msg["From"] = från
    msg["To"] = till
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP("smtp.office365.com", 587) as server:
        server.starttls()
        server.login(från, lösenord)
        server.send_message(msg)
