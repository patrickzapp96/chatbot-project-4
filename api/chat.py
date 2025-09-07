from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
import os
import smtplib
from email.message import EmailMessage
import re
from datetime import datetime, timedelta

# Neue Importe für Google Calendar
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

app = Flask(__name__)
CORS(app)

# Globale Variable zur Speicherung des Konversationsstatus
user_states = {}

# Konfiguration für Google Kalender API (Bitte anpassen!)
CLIENT_ID = "544618140213-ganesqq599qjbeeta4qspalb4blui80j.apps.googleusercontent.com")
CLIENT_SECRET = "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")
REDIRECT_URI = "https://chatbot-project-4-friseur.vercel.app/auth_callback" # Ersetze mit deiner Vercel-URL im Live-Betrieb
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

# FAQ-Datenbank
faq_db = {
    "fragen": [
        {"keywords": ["öffnungszeiten", "wann geöffnet", "wann offen", "arbeitszeit"], "antwort": "Wir sind Montag–Freitag von 9:00 bis 18:00 Uhr und Samstag von 9:00 bis 14:00 Uhr für Sie da. Sonntag ist Ruhetag."},
        {"keywords": ["termin", "vereinbaren", "buchen", "reservieren", "online"], "antwort": "Wenn Sie einen Termin vereinbaren möchten, geben Sie bitte zuerst Ihren vollständigen Namen ein."},
        {"keywords": ["adresse", "wo", "anschrift", "finden", "lage"], "antwort": "Unsere Adresse lautet: Musterstraße 12, 10115 Berlin. Wir sind zentral und gut erreichbar."},
        {"keywords": ["preise", "kosten", "gebühren", "haarschnitt"], "antwort": "Ein Damenhaarschnitt kostet ab 25 €, Herrenhaarschnitt ab 20 €. Färben ab 45 €. Die komplette Preisliste finden Sie im Salon."},
        {"keywords": ["zahlung", "karte", "bar", "visa", "mastercard", "paypal"], "antwort": "Sie können bar, mit EC-Karte, Kreditkarte (Visa/Mastercard) und sogar kontaktlos per Handy bezahlen."},
        {"keywords": ["parkplatz", "parken", "auto", "stellplatz"], "antwort": "Vor unserem Salon befinden sich kostenlose Parkplätze. Alternativ erreichen Sie uns auch gut mit den öffentlichen Verkehrsmitteln."},
        {"keywords": ["waschen", "föhnen", "styling", "legen"], "antwort": "Natürlich – wir bieten Waschen, Föhnen und individuelles Styling an. Perfekt auch für Events oder Fotoshootings."},
        {"keywords": ["färben", "farbe", "strähnen", "blondieren", "haartönung"], "antwort": "Wir färben und tönen Haare in allen Farben, inklusive Strähnen, Balayage und Blondierungen. Unsere Stylisten beraten Sie individuell."},
        {"keywords": ["dauerwelle", "locken"], "antwort": "Ja, wir bieten auch Dauerwellen und Locken-Stylings an."},
        {"keywords": ["hochzeit", "brautfrisur", "hochsteckfrisur"], "antwort": "Wir stylen wunderschöne Braut- und Hochsteckfrisuren. Am besten buchen Sie hierfür rechtzeitig einen Probetermin."},
        {"keywords": ["bart", "rasur", "bartpflege"], "antwort": "Für Herren bieten wir auch Bartpflege und Rasuren an."},
        {"keywords": ["haarpflege", "produkte", "verkaufen", "shampoo", "pflege"], "antwort": "Wir verwenden hochwertige Markenprodukte und verkaufen auch Haarpflegeprodukte, Shampoos und Stylingprodukte im Salon."},
        {"keywords": ["team", "stylist", "friseur", "mitarbeiter"], "antwort": "Unser Team besteht aus erfahrenen Stylisten, die regelmäßig an Weiterbildungen teilnehmen, um Ihnen die neuesten Trends anbieten zu können."},
        {"keywords": ["wartezeit", "sofort", "heute"], "antwort": "Kommen Sie gerne vorbei – manchmal haben wir auch spontan freie Termine. Am sichersten ist es aber, vorher kurz anzurufen."},
        {"keywords": ["verlängern", "extensions"], "antwort": "Ja, wir bieten auch Haarverlängerungen und Verdichtungen mit hochwertigen Extensions an."},
        {"keywords": ["glätten", "keratin", "straightening"], "antwort": "Wir bieten professionelle Keratin-Glättungen für dauerhaft glatte und gepflegte Haare an."},
        {"keywords": ["gutschein", "verschenken", "geschenk"], "antwort": "Ja, Sie können bei uns Gutscheine kaufen – ideal als Geschenk für Freunde und Familie!"},
        {"keywords": ["kinder", "kids", "jungen", "mädchen"], "antwort": "Natürlich schneiden wir auch Kinderhaare. Der Preis für einen Kinderhaarschnitt startet ab 15 €."},
        {"keywords": ["hygiene", "corona", "masken", "sicherheit"], "antwort": "Ihre Gesundheit liegt uns am Herzen. Wir achten auf höchste Hygienestandards und desinfizieren regelmäßig unsere Arbeitsplätze."},
        {"keywords": ["kontakt", "telefon", "nummer", "anrufen"], "antwort": "Sie erreichen uns telefonisch unter 030-123456 oder per E-Mail unter info@friseur-muster.de."}
    ],
    "fallback": "Das weiß ich leider nicht. Bitte rufen Sie uns direkt unter 030-123456 an, wir helfen Ihnen gerne persönlich weiter."
}

def create_calendar_event(request_data):
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        else:
            print("Keine gültigen Anmeldeinformationen gefunden. Bitte den /authorize-Link besuchen.")
            return False

    try:
        service = build('calendar', 'v3', credentials=creds)
        
        # Annahme: Der Kunde gibt Datum und Uhrzeit als String ein (z.B. "20. Mai um 10:00")
        # Dieser Teil ist sehr komplex. Für eine Demo kann man ein festes Format annehmen.
        # Hier ist ein Beispiel, wie man das Datum vom Nutzer-Input verarbeiten könnte:
        
        # Platzhalter für die Datumsverarbeitung
        # Das Datum muss von dir so umgewandelt werden, dass es im Format
        # 'YYYY-MM-DDTHH:MM:SS' vorliegt. Das folgende ist nur ein Beispiel.
        event_start_time = "2025-09-08T10:00:00" 
        event_end_time = "2025-09-08T11:00:00"

        event = {
            'summary': f"Termin für {request_data['service']}",
            'location': 'Dein Salon',
            'description': f"Name: {request_data['name']}\nE-Mail: {request_data['email']}",
            'start': {
                'dateTime': event_start_time,
                'timeZone': 'Europe/Berlin',
            },
            'end': {
                'dateTime': event_end_time,
                'timeZone': 'Europe/Berlin',
            },
            'attendees': [{'email': request_data['email']}],
        }

        event = service.events().insert(calendarId='primary', body=event).execute()
        return True
    except HttpError as error:
        print(f"Ein Kalenderfehler ist aufgetreten: {error}")
        return False
    except Exception as e:
        print(f"Ein unerwarteter Fehler ist aufgetreten: {e}")
        return False

@app.route('/authorize')
def authorize():
    flow = InstalledAppFlow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI]
            }
        }, SCOPES
    )

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true')

    user_states[request.remote_addr]['auth_state'] = state
    return redirect(authorization_url)

@app.route('/auth_callback')
def auth_callback():
    state = user_states[request.remote_addr].get('auth_state')
    
    flow = InstalledAppFlow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI]
            }
        }, SCOPES, state=state
    )

    try:
        flow.fetch_token(authorization_response=request.url)
        creds = flow.credentials
        
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
        
        return "Authentifizierung erfolgreich. Sie können zum Chatbot zurückkehren."
    except Exception as e:
        return f"Authentifizierungsfehler: {e}"

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

        if current_state == "initial":
            cleaned_message = re.sub(r'[^\w\s]', '', user_message)
            user_words = set(cleaned_message.split())
            best_match_score = 0
            
            if any(keyword in user_message for keyword in ["termin", "buchen", "vereinbaren"]):
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
            response_text = "Wann (Datum und Uhrzeit) würden Sie den Termin gerne wahrnehmen?"
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
                
                # Versuch, ein Kalender-Event zu erstellen
                if create_calendar_event(request_data):
                    response_text = "Vielen Dank! Ihr Termin wurde erfolgreich in den Kalender eingetragen."
                else:
                    response_text = "Entschuldigung, der Termin konnte nicht im Kalender eingetragen werden. Bitte rufen Sie uns direkt an."
                
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


