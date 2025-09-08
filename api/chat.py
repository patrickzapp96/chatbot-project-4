from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import smtplib
from email.message import EmailMessage
import re
from icalendar import Calendar, Event
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Globale Variable zur Speicherung des Konversationsstatus
user_states = {}

# FAQ-Datenbank
faq_db = {
    "fragen": [
        {"keywords": ["öffnungszeiten", "wann geöffnet", "wann offen", "arbeitszeit"], "antwort": "Wir sind Montag–Freitag von 9:00 bis 18:00 Uhr und Samstag von 9:00 bis 14:00 Uhr für Sie da. Sonntag ist Ruhetag."},
        {"keywords": ["termin", "vereinbaren", "buchen", "reservieren", "online"], "antwort": "Wenn Sie einen Termin vereinbaren möchten, geben Sie bitte zuerst Ihren vollständigen Namen ein."},
        {"keywords": ["adresse", "wo", "anschrift", "finden", "lage"], "antwort": "Unsere Adresse lautet: Musterstraße 12, 10115 Berlin. Wir sind zentral und gut erreichbar."},
        {"keywords": ["preise", "kosten", "kostet", "gebühren", "haarschnitt", "herrenhaarschnitt", "damenhaarschnitt"], "antwort": "Ein Damenhaarschnitt kostet ab 25 €, Herrenhaarschnitt ab 20 €. Färben ab 45 €. Die komplette Preisliste finden Sie im Salon."},
        {"keywords": ["zahlung", "karte", "bar", "visa", "mastercard", "paypal", "kartenzahlung", "kontaktlos", "bezahlen"], "antwort": "Sie können bar, mit EC-Karte, Kreditkarte (Visa/Mastercard) und sogar kontaktlos per Handy bezahlen."},
        {"keywords": ["parkplatz", "parken", "auto", "stellplatz"], "antwort": "Vor unserem Salon befinden sich kostenlose Parkplätze. Alternativ erreichen Sie uns auch gut mit den öffentlichen Verkehrsmitteln."},
        {"keywords": ["waschen", "föhnen", "styling", "legen"], "antwort": "Natürlich – wir bieten Waschen, Föhnen und individuelles Styling an. Perfekt auch für Events oder Fotoshootings."},
        {"keywords": ["färben", "farbe", "farben", "strähnen", "blondieren", "haartönung"], "antwort": "Wir färben und tönen Haare in allen Farben, inklusive Strähnen, Balayage und Blondierungen. Unsere Stylisten beraten Sie individuell."},
        {"keywords": ["dauerwelle", "dauerwellen", "lockenfrisuren", "locken", "lockenfrisur"], "antwort": "Ja, wir bieten auch Dauerwellen und Locken-Stylings an."},
        {"keywords": ["hochzeit", "brautfrisur", "brautfrisuren", "hochsteckfrisur"], "antwort": "Wir stylen wunderschöne Braut- und Hochsteckfrisuren. Am besten buchen Sie hierfür rechtzeitig einen Probetermin."},
        {"keywords": ["bart", "rasur", "bartpflege"], "antwort": "Für Herren bieten wir auch Bartpflege und Rasuren an."},
        {"keywords": ["haarpflege", "produkte", "verkaufen", "shampoo", "pflege"], "antwort": "Wir verwenden hochwertige Markenprodukte und verkaufen auch Haarpflegeprodukte, Shampoos und Stylingprodukte im Salon."},
        {"keywords": ["team", "stylist", "friseur", "mitarbeiter"], "antwort": "Unser Team besteht aus erfahrenen Stylisten, die regelmäßig an Weiterbildungen teilnehmen, um Ihnen die neuesten Trends anbieten zu können."},
        {"keywords": ["wartezeit", "sofort", "heute", "spontan"], "antwort": "Kommen Sie gerne vorbei – manchmal haben wir auch spontan freie Termine. Am sichersten ist es aber, vorher kurz anzurufen unter 030-123456"},
        {"keywords": ["verlängern", "extensions"], "antwort": "Ja, wir bieten auch Haarverlängerungen und Verdichtungen mit hochwertigen Extensions an."},
        {"keywords": ["glätten", "keratin", "straightening"], "antwort": "Wir bieten professionelle Keratin-Glättungen für dauerhaft glatte und gepflegte Haare an."},
        {"keywords": ["gutschein", "gutscheine", "verschenken", "geschenk"], "antwort": "Ja, Sie können bei uns Gutscheine kaufen – ideal als Geschenk für Freunde und Familie!"},
        {"keywords": ["kinder", "kids", "jungen", "mädchen", "sohn", "tochter"], "antwort": "Natürlich schneiden wir auch Kinderhaare. Der Preis für einen Kinderhaarschnitt startet ab 15 €."},
        {"keywords": ["hygiene", "corona", "masken", "sicherheit"], "antwort": "Ihre Gesundheit liegt uns am Herzen. Wir achten auf höchste Hygienestandards und desinfizieren regelmäßig unsere Arbeitsplätze."},
        {"keywords": ["kontakt", "kontaktdaten", "telefonnummer", "telefon", "nummer", "anrufen"], "antwort": "Sie erreichen uns telefonisch unter 030-123456 oder per E-Mail unter info@friseur-muster.de."}
    ],
    "fallback": "Das weiß ich leider nicht. Bitte rufen Sie uns direkt unter 030-123456 an, wir helfen Ihnen gerne persönlich weiter."
}

def send_appointment_request(request_data):
    """
    Diese Funktion sendet eine E-Mail mit der Terminanfrage und einem Kalenderanhang.
    """
    sender_email = os.environ.get("SENDER_EMAIL")
    sender_password = os.environ.get("SENDER_PASSWORD")
    receiver_email = os.environ.get("RECEIVER_EMAIL")

    if not all([sender_email, sender_password, receiver_email]):
        print("E-Mail-Konfiguration fehlt. E-Mail kann nicht gesendet werden.")
        return False

    msg = EmailMessage()
    msg['Subject'] = "Neue Terminanfrage über den Chatbot"
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Reply-To'] = request_data.get('email', 'no-reply@example.com')

    # Text der E-Mail
    email_text = f"""
    Hallo Geschäftsführer,
    
    Sie haben eine neue Terminanfrage über den Chatbot erhalten:
    
    Name: {request_data.get('name', 'N/A')}
    E-Mail: {request_data.get('email', 'N/A')}
    Service: {request_data.get('service', 'N/A')}
    Datum & Uhrzeit: {request_data.get('date_time', 'N/A')}
    
    Bitte bestätigen Sie diesen Termin manuell im Kalender oder kontaktieren Sie den Kunden direkt.
    """
    msg.set_content(email_text)

    # Erstelle den Kalendereintrag
    cal = Calendar()
    event = Event()

    try:
        start_time_str = request_data.get('date_time')
        # Annahme: request_data['date_time'] hat das Format 'DD.MM.YYYY HH:MM'
        start_time = datetime.strptime(start_time_str, '%d.%m.%Y %H:%M')
    except (ValueError, TypeError) as e:
        print(f"Fehler bei der Konvertierung des Datums: {e}")
        return False

    event.add('dtstart', start_time)
    event.add('summary', f"Termin mit {request_data.get('name', 'Kunde')}")
    event.add('description', f"Service: {request_data.get('service', 'N/A')}\nE-Mail: {request_data.get('email', 'N/A')}")
    event.add('location', 'Musterstraße 12, 10115 Berlin')
    
    cal.add_component(event)

    # Erstelle einen Anhang aus dem Kalenderobjekt
    ics_file = cal.to_ical()
    msg.add_attachment(ics_file, maintype='text', subtype='calendar', filename='Termin.ics')
    
    # Sende die E-Mail
    try:
        with smtplib.SMTP_SSL("smtp.web.de", 465) as smtp:
            smtp.login(sender_email, sender_password)
            smtp.send_message(msg)
        return True
    except Exception as e:
        print(f"Fehler beim Senden der E-Mail: {e}")
        return False

@app.route('/api/chat', methods=['POST'])
def chat_handler():
    try:
        if not request.is_json:
            return jsonify({"error": "Fehlende JSON-Nachricht"}), 400

        user_message = request.json.get('message', '').lower
