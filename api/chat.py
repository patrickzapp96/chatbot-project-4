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
        {
            "id": 1,
            "kategorie": "Öffnungszeiten",
            "titel": "Öffnungszeiten",
            "keywords": ["öffnungszeiten", "wann", "geöffnet", "offen", "arbeitszeit"],
            "antwort": "Wir sind Montag–Freitag von 9:00 bis 18:00 Uhr und Samstag von 9:00 bis 14:00 Uhr für Sie da. Sonntag ist Ruhetag."
        },
        {
            "id": 2,
            "kategorie": "Terminbuchung",
            "titel": "Termin vereinbaren",
            "keywords": ["termin buchen", "termin vereinbaren", "termin ausmachen", "buchen", "vereinbaren", "ausmachen", "reservieren", "online"],
            "antwort": "Wenn Sie einen Termin vereinbaren möchten, geben Sie bitte zuerst Ihren vollständigen Namen ein."
        },
        {
            "id": 3,
            "kategorie": "Allgemein",
            "titel": "Adresse",
            "keywords": ["adresse", "wo", "anschrift", "finden", "lage"],
            "antwort": "Unsere Adresse lautet: Musterstraße 12, 10115 Berlin. Wir sind zentral und gut erreichbar."
        },
        {
            "id": 4,
            "kategorie": "Preise",
            "titel": "Preise und Kosten",
            "keywords": ["preise", "kosten", "kostet", "gebühren", "haarschnitt", "herrenhaarschnitt", "damenhaarschnitt"],
            "antwort": "Ein Damenhaarschnitt kostet ab 25 €, Herrenhaarschnitt ab 20 €. Färben ab 45 €. Die komplette Preisliste finden Sie im Salon."
        },
        {
            "id": 5,
            "kategorie": "Zahlung",
            "titel": "Zahlungsmethoden",
            "keywords": ["zahlung", "karte", "bar", "visa", "mastercard", "paypal", "kartenzahlung", "kontaktlos", "bezahlen"],
            "antwort": "Sie können bar, mit EC-Karte, Kreditkarte (Visa/Mastercard) und sogar kontaktlos per Handy bezahlen."
        },
        {
            "id": 6,
            "kategorie": "Allgemein",
            "titel": "Parkmöglichkeiten",
            "keywords": ["parkplatz", "parken", "auto", "stellplatz"],
            "antwort": "Vor unserem Salon befinden sich kostenlose Parkplätze. Alternativ erreichen Sie uns auch gut mit den öffentlichen Verkehrsmitteln."
        },
        {
            "id": 7,
            "kategorie": "Services",
            "titel": "Waschen und Föhnen",
            "keywords": ["waschen", "föhnen", "styling", "legen"],
            "antwort": "Natürlich – wir bieten Waschen, Föhnen und individuelles Styling an. Perfekt auch für Events oder Fotoshootings."
        },
        {
            "id": 8,
            "kategorie": "Services",
            "titel": "Haare färben",
            "keywords": ["färben", "farbe", "farben", "strähnen", "blondieren", "haartönung"],
            "antwort": "Wir färben und tönen Haare in allen Farben, inklusive Strähnen, Balayage und Blondierungen. Unsere Stylisten beraten Sie individuell."
        },
        {
            "id": 9,
            "kategorie": "Services",
            "titel": "Dauerwelle",
            "keywords": ["dauerwelle", "dauerwellen", "lockenfrisuren", "locken", "lockenfrisur"],
            "antwort": "Ja, wir bieten auch Dauerwellen und Locken-Stylings an."
        },
        {
            "id": 10,
            "kategorie": "Services",
            "titel": "Braut- und Hochsteckfrisuren",
            "keywords": ["hochzeit", "brautfrisur", "brautfrisuren", "hochsteckfrisur"],
            "antwort": "Wir stylen wunderschöne Braut- und Hochsteckfrisuren. Am besten buchen Sie hierfür rechtzeitig einen Probetermin."
        },
        {
            "id": 11,
            "kategorie": "Services",
            "titel": "Bartpflege",
            "keywords": ["bart", "rasur", "bartpflege"],
            "antwort": "Für Herren bieten wir auch Bartpflege und Rasuren an."
        },
        {
            "id": 12,
            "kategorie": "Produkte",
            "titel": "Verkauf von Haarpflegeprodukten",
            "keywords": ["haarpflege", "produkte", "verkaufen", "shampoo", "pflege"],
            "antwort": "Wir verwenden hochwertige Markenprodukte und verkaufen auch Haarpflegeprodukte, Shampoos und Stylingprodukte im Salon."
        },
        {
            "id": 13,
            "kategorie": "Allgemein",
            "titel": "Das Team",
            "keywords": ["team", "stylist", "friseur", "mitarbeiter"],
            "antwort": "Unser Team besteht aus erfahrenen Stylisten, die regelmäßig an Weiterbildungen teilnehmen, um Ihnen die neuesten Trends anbieten zu können."
        },
        {
            "id": 14,
            "kategorie": "Terminbuchung",
            "titel": "Spontane Termine",
            "keywords": ["warten", "wartezeit", "sofort", "heute", "spontan"],
            "antwort": "Kommen Sie gerne vorbei – manchmal haben wir auch spontan freie Termine. Am sichersten ist es aber, vorher kurz anzurufen unter 030-123456"
        },
        {
            "id": 15,
            "kategorie": "Services",
            "titel": "Haarverlängerung",
            "keywords": ["verlängern", "extensions", "haarverlängerungen", "verlängerung", "haarverlängerung"],
            "antwort": "Ja, wir bieten auch Haarverlängerungen und Verdichtungen mit hochwertigen Extensions an."
        },
        {
            "id": 16,
            "kategorie": "Services",
            "titel": "Haar glätten",
            "keywords": ["glätten", "keratin", "straightening"],
            "antwort": "Wir bieten professionelle Keratin-Glättungen für dauerhaft glatte und gepflegte Haare an."
        },
        {
            "id": 17,
            "kategorie": "Produkte",
            "titel": "Gutscheine kaufen",
            "keywords": ["gutschein", "gutscheine", "verschenken", "geschenk"],
            "antwort": "Ja, Sie können bei uns Gutscheine kaufen – ideal als Geschenk für Freunde und Familie!"
        },
        {
            "id": 18,
            "kategorie": "Services",
            "titel": "Kinderhaarschnitt",
            "keywords": ["kinder", "kids", "jungen", "mädchen", "sohn", "tochter"],
            "antwort": "Natürlich schneiden wir auch Kinderhaare. Der Preis für einen Kinderhaarschnitt startet ab 15 €."
        },
        {
            "id": 19,
            "kategorie": "Hygiene",
            "titel": "Hygienestandards",
            "keywords": ["hygiene", "corona", "masken", "sicherheit"],
            "antwort": "Ihre Gesundheit liegt uns am Herzen. Wir achten auf höchste Hygienestandards und desinfizieren regelmäßig unsere Arbeitsplätze."
        },
        {
            "id": 20,
            "kategorie": "Allgemein",
            "titel": "Kontakt",
            "keywords": ["kontakt", "kontaktdaten", "telefonnummer", "telefon", "nummer", "anrufen"],
            "antwort": "Sie erreichen uns telefonisch unter 030-123456 oder per E-Mail unter info@friseur-muster.de."
        },
        {
            "id": 21,
            "kategorie": "Services",
            "titel": "Balayage und Strähnchen",
            "keywords": ["balayage", "strähnchen", "highlights", "lowlights"],
            "antwort": "Wir sind Spezialisten für Balayage, Highlights und Lowlights. Unsere Stylisten kreieren natürliche Farbverläufe, die Ihr Haar zum Strahlen bringen."
        },
        {
            "id": 22,
            "kategorie": "Services",
            "titel": "Olaplex-Behandlung",
            "keywords": ["olaplex", "haarpflege", "kur", "stärkung", "haare reparieren", "reparieren"],
            "antwort": "Wir bieten eine professionelle Olaplex-Behandlung an, die Haarschäden repariert, die Haarstruktur stärkt und für gesundes, glänzendes Haar sorgt."
        },
        {
            "id": 23,
            "kategorie": "Services",
            "titel": "Trockenhaarschnitt",
            "keywords": ["trockenhaarschnitt", "trockenschnitt", "ohne waschen", "schnell"],
            "antwort": "Ein Trockenhaarschnitt ist bei uns nach Absprache möglich. Er ist ideal, wenn Sie wenig Zeit haben oder einfach nur die Spitzen geschnitten haben möchten."
        },
        {
            "id": 24,
            "kategorie": "Terminbuchung",
            "titel": "Termin stornieren",
            "keywords": ["stornieren", "termin stornieren", "termin absagen", "verschieben", "nicht kommen"],
            "antwort": "Sie können Ihren Termin bis zu 24 Stunden vorher telefonisch unter 030-123456 oder per E-Mail an info@friseur-muster.de absagen. Bei Nichterscheinen behalten wir uns vor, eine Ausfallgebühr zu berechnen."
        },
        {
            "id": 25,
            "kategorie": "Allgemein",
            "titel": "Barrierefreiheit",
            "keywords": ["rollstuhl", "barrierefrei", "zugang", "barrierefreiheit"],
            "antwort": "Unser Salon ist barrierefrei zugänglich, sodass auch Rollstuhlfahrer problemlos zu uns kommen können."
        },
        {
            "id": 26,
            "kategorie": "Allgemein",
            "titel": "Haustiere",
            "keywords": ["hund", "haustier", "tiere"],
            "antwort": "Aus hygienischen Gründen und im Interesse aller Kunden sind Haustiere in unserem Salon leider nicht gestattet."
        }
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

        user_message = request.json.get('message', '').lower()
        user_ip = request.remote_addr
        
        if user_ip not in user_states:
            user_states[user_ip] = {"state": "initial"}
            
        current_state = user_states[user_ip]["state"]
        response_text = faq_db['fallback']

        # Überprüfe den aktuellen Konversationsstatus
        if current_state == "initial":
            cleaned_message = re.sub(r'[^\w\s]', '', user_message)
            user_words = set(cleaned_message.split())
            best_match_score = 0
            
            if any(keyword in user_message for keyword in ["termin buchen", "termin vereinbaren", "termin ausmachen", "termin buchen", "termin reservieren"]):
                response_text = "Gerne. Wie lautet Ihr vollständiger Name?"
                user_states[user_ip] = {"state": "waiting_for_name"}
            else:
                for item in faq_db['fragen']:
                    keyword_set = set(item['keywords'])
                    intersection = user_words.intersection(keyword_set)
                    score = len(intersection)
                    
                    if score > best_match_score:
                        best_match_score = score
                        response_text = item['antwort']
            
        elif current_state == "waiting_for_name":
            user_states[user_ip]["name"] = user_message
            response_text = "Vielen Dank. Wie lautet Ihre E-Mail-Adresse?"
            user_states[user_ip]["state"] = "waiting_for_email"

        elif current_state == "waiting_for_email":
            email_regex = r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$'
            if re.match(email_regex, user_message):
                user_states[user_ip]["email"] = user_message
                response_text = "Alles klar. Welchen Service möchten Sie buchen (z.B. Haarschnitt, Färben, Bartpflege)?"
                user_states[user_ip]["state"] = "waiting_for_service"
            else:
                response_text = "Das scheint keine gültige E-Mail-Adresse zu sein. Bitte geben Sie eine korrekte E-Mail-Adresse ein."
        
        elif current_state == "waiting_for_service":
            user_states[user_ip]["service"] = user_message
            response_text = "Wann würden Sie den Termin gerne wahrnehmen? Bitte geben Sie das Datum und die Uhrzeit im Format **TT.MM.JJJJ HH:MM** ein, z.B. **15.10.2025 14:00**."
            user_states[user_ip]["state"] = "waiting_for_datetime"

        elif current_state == "waiting_for_datetime":
            user_states[user_ip]["date_time"] = user_message
            
            data = user_states[user_ip]
            response_text = (
                f"Bitte überprüfen Sie Ihre Angaben:\n"
                f"Name: {data.get('name', 'N/A')}\n"
                f"E-Mail: {data.get('email', 'N/A')}\n"
                f"Service: {data.get('service', 'N/A')}\n"
                f"Datum und Uhrzeit: {data.get('date_time', 'N/A')}\n\n"
                f"Möchten Sie die Anfrage so absenden? Bitte antworten Sie mit 'Ja' oder 'Nein'."
            )
            user_states[user_ip]["state"] = "waiting_for_confirmation"
        
        elif current_state == "waiting_for_confirmation":
            if user_message in ["ja", "ja, das stimmt", "bestätigen", "ja bitte"]:
                request_data = {
                    "name": user_states[user_ip].get("name", "N/A"),
                    "email": user_states[user_ip].get("email", "N/A"),
                    "service": user_states[user_ip].get("service", "N/A"),
                    "date_time": user_states[user_ip].get("date_time", "N/A"),
                }
                
                if send_appointment_request(request_data):
                    response_text = "Vielen Dank! Ihre Terminanfrage wurde erfolgreich übermittelt. Wir werden uns in Kürze bei Ihnen melden."
                else:
                    response_text = "Entschuldigung, es gab ein Problem beim Senden Ihrer Anfrage. Bitte rufen Sie uns direkt an."
                
                user_states[user_ip]["state"] = "initial"
            
            elif user_message in ["nein", "abbrechen", "falsch"]:
                response_text = "Die Terminanfrage wurde abgebrochen. Falls Sie die Eingabe korrigieren möchten, beginnen Sie bitte erneut mit 'Termin vereinbaren'."
                user_states[user_ip]["state"] = "initial"
            
            else:
                response_text = "Bitte antworten Sie mit 'Ja' oder 'Nein'."
        
        return jsonify({"reply": response_text})

    except Exception as e:
        print(f"Ein Fehler ist aufgetreten: {e}")
        return jsonify({"error": "Interner Serverfehler"}), 500

if __name__ == '__main__':
    app.run(debug=True)







