from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import smtplib
from email.message import EmailMessage
import re
from icalendar import Calendar, Event # Importiert das iCalendar-Modul
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Globale Variable zur Speicherung des Konversationsstatus
user_states = {}

# FAQ-Datenbank
faq_db = {
    "fragen": [
        {"keywords": ["öffnungszeiten", "wann geöffnet", "wann offen", "arbeitszeit"], "antwort": "Wir sind Montag–Freitag von 9:00 bis 18:00 Uhr und Samstag von 9:00 bis 14:00 Uhr für Sie da. Sonntag ist Ruhetag."},
        [cite_start]{"keywords": ["termin", "vereinbaren", "buchen", "reservieren", "online"], "antwort": "Wenn Sie einen Termin vereinbaren möchten, geben Sie bitte zuerst Ihren vollständigen Namen ein." [cite: 80]},
        [cite_start]{"keywords": ["adresse", "wo", "anschrift", "finden", "lage"], "antwort": "Unsere Adresse lautet: Musterstraße 12, 10115 Berlin. Wir sind zentral und gut erreichbar." [cite: 80]},
        [cite_start]{"keywords": ["preise", "kosten", "kostet", "gebühren", "haarschnitt", "herrenhaarschnitt", "damenhaarschnitt"], "antwort": "Ein Damenhaarschnitt kostet ab 25 €, Herrenhaarschnitt ab 20 €. Färben ab 45 €. Die komplette Preisliste finden Sie im Salon." [cite: 81]},
        [cite_start]{"keywords": ["zahlung", "karte", "bar", "visa", "mastercard", "paypal", "kartenzahlung", "kontaktlos", "bezahlen"], "antwort": "Sie können bar, mit EC-Karte, Kreditkarte (Visa/Mastercard) und sogar kontaktlos per Handy bezahlen." [cite: 81]},
        [cite_start]{"keywords": ["parkplatz", "parken", "auto", "stellplatz"], "antwort": "Vor unserem Salon befinden sich kostenlose Parkplätze. Alternativ erreichen Sie uns auch gut mit den öffentlichen Verkehrsmitteln." [cite: 82]},
        [cite_start]{"keywords": ["waschen", "föhnen", "styling", "legen"], "antwort": "Natürlich – wir bieten Waschen, Föhnen und individuelles Styling an. Perfekt auch für Events oder Fotoshootings." [cite: 83]},
        [cite_start]{"keywords": ["färben", "farbe", "farben", "strähnen", "blondieren", "haartönung"], "antwort": "Wir färben und tönen Haare in allen Farben, inklusive Strähnen, Balayage und Blondierungen. Unsere Stylisten beraten Sie individuell." [cite: 84]},
        {"keywords": ["dauerwelle", "dauerwellen", "lockenfrisuren", "locken", "lockenfrisur"], "antwort": "Ja, wir bieten auch Dauerwellen und Locken-Stylings an."},
        [cite_start]{"keywords": ["hochzeit", "brautfrisur", "brautfrisuren", "hochsteckfrisur"], "antwort": "Wir stylen wunderschöne Braut- und Hochsteckfrisuren. Am besten buchen Sie hierfür rechtzeitig einen Probetermin." [cite: 85]},
        {"keywords": ["bart", "rasur", "bartpflege"], "antwort": "Für Herren bieten wir auch Bartpflege und Rasuren an."},
        {"keywords": ["haarpflege", "produkte", "verkaufen", "shampoo", "pflege"], "antwort": "Wir verwenden hochwertige Markenprodukte und verkaufen auch Haarpflegeprodukte, Shampoos und Stylingprodukte im Salon."},
        {"keywords": ["team", "stylist", "friseur", "mitarbeiter"], "antwort": "Unser Team besteht aus erfahrenen Stylisten, die regelmäßig an Weiterbildungen teilnehmen, um Ihnen die neuesten Trends anbieten zu können."},
        [cite_start]{"keywords": ["wartezeit", "sofort", "heute", "spontan"], "antwort": "Kommen Sie gerne vorbei – manchmal haben wir auch spontan freie Termine. Am sichersten ist es aber, vorher kurz anzurufen unter 030-123456" [cite: 86, 87]},
        {"keywords": ["verlängern", "extensions"], "antwort": "Ja, wir bieten auch Haarverlängerungen und Verdichtungen mit hochwertigen Extensions an."},
        {"keywords": ["glätten", "keratin", "straightening"], "antwort": "Wir bieten professionelle Keratin-Glättungen für dauerhaft glatte und gepflegte Haare an."},
        {"keywords": ["gutschein", "gutscheine", "verschenken", "geschenk"], "antwort": "Ja, Sie können bei uns Gutscheine kaufen – ideal als Geschenk für Freunde und Familie!"},
        [cite_start]{"keywords": ["kinder", "kids", "jungen", "mädchen", "sohn", "tochter"], "antwort": "Natürlich schneiden wir auch Kinderhaare. Der Preis für einen Kinderhaarschnitt startet ab 15 €." [cite: 88]},
        [cite_start]{"keywords": ["hygiene", "corona", "masken", "sicherheit"], "antwort": "Ihre Gesundheit liegt uns am Herzen. Wir achten auf höchste Hygienestandards und desinfizieren regelmäßig unsere Arbeitsplätze." [cite: 89]},
        {"keywords": ["kontakt", "kontaktdaten", "telefonnummer", "telefon", "nummer", "anrufen"], "antwort": "Sie erreichen uns telefonisch unter 030-123456 oder per E-Mail unter info@friseur-muster.de."}
    ],
    [cite_start]"fallback": "Das weiß ich leider nicht. Bitte rufen Sie uns direkt unter 030-123456 an, wir helfen Ihnen gerne persönlich weiter." [cite: 90]
}

def send_appointment_request(request_data):
    """
    Diese Funktion sendet eine E-Mail mit der Terminanfrage und einem Kalenderanhang.
    [cite_start]""" [cite: 91]
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
    [cite_start]""" [cite: 92]
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
        [cite_start]print(f"Fehler beim Senden der E-Mail: {e}") [cite: 93]
        return False

@app.route('/api/chat', methods=['POST'])
def chat_handler():
    try:
        if not request.is_json:
            return jsonify({"error": "Fehlende JSON-Nachricht"}), 400

        user_message = request.json.get('message', '').lower()
        user_ip = request.remote_addr
        
        if user_ip not in user_states:
            [cite_start]user_states[user_ip] = {"state": "initial"} [cite: 94]
            
        current_state = user_states[user_ip]["state"]
        [cite_start]response_text = faq_db['fallback'] [cite: 90]

        # Überprüfe den aktuellen Konversationsstatus
        if current_state == "initial":
            [cite_start]cleaned_message = re.sub(r'[^\w\s]', '', user_message) [cite: 95]
            user_words = set(cleaned_message.split())
            best_match_score = 0
            
            if any(keyword in user_message for keyword in ["termin", "buchen", "vereinbaren"]):
                [cite_start]response_text = "Gerne. Wie lautet Ihr vollständiger Name?" [cite: 96]
                [cite_start]user_states[user_ip] = {"state": "waiting_for_name"} [cite: 96]
            else:
                for item in faq_db['fragen']:
                    keyword_set = set(item['keywords'])
                    intersection = user_words.intersection(keyword_set)
                    [cite_start]score = len(intersection) [cite: 97]
                    
                    if score > best_match_score:
                        best_match_score = score
                        [cite_start]response_text = item['antwort'] [cite: 98]
            
        elif current_state == "waiting_for_name":
            user_states[user_ip]["name"] = user_message
            [cite_start]response_text = "Vielen Dank. Wie lautet Ihre E-Mail-Adresse?" [cite: 99]
            [cite_start]user_states[user_ip]["state"] = "waiting_for_email" [cite: 99]

        elif current_state == "waiting_for_email":
            email_regex = r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$'
            if re.match(email_regex, user_message):
                user_states[user_ip]["email"] = user_message
                [cite_start]response_text = "Alles klar. Welchen Service möchten Sie buchen (z.B. Haarschnitt, Färben, Bartpflege)?" [cite: 100, 101]
                [cite_start]user_states[user_ip]["state"] = "waiting_for_service" [cite: 101]
            else:
                [cite_start]response_text = "Das scheint keine gültige E-Mail-Adresse zu sein. Bitte geben Sie eine korrekte E-Mail-Adresse ein." [cite: 102]
        
        elif current_state == "waiting_for_service":
            user_states[user_ip]["service"] = user_message
            [cite_start]response_text = "Wann (Datum und Uhrzeit) würden Sie den Termin gerne wahrnehmen?" [cite: 102]
            [cite_start]user_states[user_ip]["state"] = "waiting_for_datetime" [cite: 103]

        elif current_state == "waiting_for_datetime":
            user_states[user_ip]["date_time"] = user_message
            
            data = user_states[user_ip]
            response_text = (
                [cite_start]f"Bitte überprüfen Sie Ihre Angaben:\n" [cite: 104]
                f"Name: {data.get('name', 'N/A')}\n"
                f"E-Mail: {data.get('email', 'N/A')}\n"
                f"Service: {data.get('service', 'N/A')}\n"
                f"Datum und Uhrzeit: {data.get('date_time', 'N/A')}\n\n"
                [cite_start]f"Möchten Sie die Anfrage so absenden? Bitte antworten Sie mit 'Ja' oder 'Nein'." [cite: 105]
            )
            [cite_start]user_states[user_ip]["state"] = "waiting_for_confirmation" [cite: 105]
        
        elif current_state == "waiting_for_confirmation":
            if user_message in ["ja", "ja, das stimmt", "bestätigen", "ja bitte"]:
                request_data = {
                    "name": user_states[user_ip].get("name", "N/A"),
                    "email": user_states[user_ip].get("email", "N/A"),
                    "service": user_states[user_ip].get("service", "N/A"),
                    "date_time": user_states[user_ip].get("date_time", "N/A"),
                [cite_start]} [cite: 106, 107]
                
                if send_appointment_request(request_data):
                    [cite_start]response_text = "Vielen Dank! Ihre Terminanfrage wurde erfolgreich übermittelt. Wir werden uns in Kürze bei Ihnen melden." [cite: 108]
                else:
                    [cite_start]response_text = "Entschuldigung, es gab ein Problem beim Senden Ihrer Anfrage. Bitte rufen Sie uns direkt an." [cite: 109]
                
                [cite_start]user_states[user_ip]["state"] = "initial" [cite: 109]
            
            elif user_message in ["nein", "abbrechen", "falsch"]:
                [cite_start]response_text = "Die Terminanfrage wurde abgebrochen. Falls Sie die Eingabe korrigieren möchten, beginnen Sie bitte erneut mit 'Termin vereinbaren'." [cite: 110, 111]
                [cite_start]user_states[user_ip]["state"] = "initial" [cite: 111]
            
            else:
                [cite_start]response_text = "Bitte antworten Sie mit 'Ja' oder 'Nein'." [cite: 112]
        
        [cite_start]return jsonify({"reply": response_text}) [cite: 112]

    except Exception as e:
        [cite_start]print(f"Ein Fehler ist aufgetreten: {e}") [cite: 112]
        return jsonify({"error": "Interner Serverfehler"}), 500

if __name__ == '__main__':
    app.run(debug=True)
