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
# FÜR LOKALE ENTWICKLUNG: Ersetze die Platzhalter mit deinen tatsächlichen Werten
# VOR DEM HOCHLADEN AUF VERCEL: Ändere diese wieder zu os.environ.get(...)
CLIENT_ID = "544618140213-ganesqq599qjbeeta4qspalb4blui80j.apps.googleusercontent.com"
CLIENT_SECRET = "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"
REDIRECT_URI = "http://localhost:5000/auth_callback"
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
    ]
}

# Hilfsfunktion, um Keywords in einer Nachricht zu finden
def find_keywords(message):
    message = message.lower()
    for entry in faq_db["fragen"]:
        for keyword in entry["keywords"]:
            if keyword in message:
                return entry["antwort"]
    return None

# Funktion zur Validierung der E-Mail-Adresse
def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def create_calendar_event(data):
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            return False # Autorisierung erforderlich
    
    try:
        service = build('calendar', 'v3', credentials=creds)
        
        event_body = {
            'summary': f'Termin: {data["service"]}',
            'description': f'Name: {data["name"]}\nE-Mail: {data["email"]}',
            'start': {
                'dateTime': data["date_time"],
                'timeZone': 'Europe/Berlin',
            },
            'end': {
                'dateTime': data["date_time"],
                'timeZone': 'Europe/Berlin',
            },
            'attendees': [
                {'email': data["email"]},
            ],
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 10},
                ],
            },
        }

        event = service.events().insert(calendarId='primary', body=event_body).execute()
        return True
    
    except HttpError as error:
        print(f"Ein HTTP-Fehler ist aufgetreten: {error}")
        return False
    except Exception as e:
        print(f"Ein Fehler ist aufgetreten: {e}")
        return False

# Die Route, die den Google OAuth-Flow startet
@app.route("/authorize")
def authorize():
    flow = InstalledAppFlow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uris": [REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://accounts.google.com/o/oauth2/token",
            }
        },
        SCOPES,
    )
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true')
    return redirect(authorization_url)

# Die Route, zu der Google zurückleitet
@app.route("/auth_callback")
def auth_callback():
    code = request.args.get('code')
    flow = InstalledAppFlow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uris": [REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://accounts.google.com/o/oauth2/token",
            }
        },
        SCOPES,
        state=request.args.get('state'),
    )
    flow.fetch_token(code=code)
    creds = flow.credentials
    with open("token.json", "w") as token:
        token.write(creds.to_json())
    return "Authentifizierung erfolgreich! Die token.json-Datei wurde erstellt. Sie können dieses Fenster nun schließen."

@app.route("/api/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "")
    user_ip = request.remote_addr
    user_message_lower = user_message.lower()

    if user_ip not in user_states:
        user_states[user_ip] = {"state": "initial"}
    
    current_state = user_states[user_ip]["state"]
    response_text = ""

    try:
        if current_state == "initial":
            if "termin" in user_message_lower:
                response_text = "Gerne! Für eine Terminanfrage benötige ich Ihren Namen, Ihre E-Mail, die gewünschte Dienstleistung, das Datum und die Uhrzeit."
                user_states[user_ip]["state"] = "waiting_for_name"
            else:
                faq_answer = find_keywords(user_message)
                if faq_answer:
                    response_text = faq_answer
                else:
                    response_text = "Entschuldigung, ich habe Sie nicht verstanden. Kann ich Ihnen anderweitig behilflich sein?"
        
        elif current_state == "waiting_for_name":
            user_states[user_ip]["name"] = user_message
            response_text = "Vielen Dank! Bitte geben Sie nun Ihre E-Mail-Adresse ein."
            user_states[user_ip]["state"] = "waiting_for_email"
            
        elif current_state == "waiting_for_email":
            if is_valid_email(user_message):
                user_states[user_ip]["email"] = user_message
                response_text = "Alles klar. Welche Dienstleistung wünschen Sie?"
                user_states[user_ip]["state"] = "waiting_for_service"
            else:
                response_text = "Das scheint keine gültige E-Mail-Adresse zu sein. Bitte versuchen Sie es erneut."
        
        elif current_state == "waiting_for_service":
            user_states[user_ip]["service"] = user_message
            response_text = "Danke. Welches Datum und welche Uhrzeit schwebt Ihnen vor? (z.B. 'Freitag, 15:00 Uhr')"
            user_states[user_ip]["state"] = "waiting_for_date_time"
            
        elif current_state == "waiting_for_date_time":
            # Vereinfachte Logik zur Verarbeitung von Datum und Uhrzeit
            try:
                # Versuch, Datum und Uhrzeit zu extrahieren
                today = datetime.now()
                # Dummy-Logik, um Datum und Uhrzeit zu extrahieren
                # Du musst dies durch eine robustere Logik ersetzen
                date_time_str = user_message # Annahme: Nutzer gibt ein parsebares Format ein
                date_time = datetime.now().isoformat()
                
                user_states[user_ip]["date_time"] = date_time
                
                # Bestätigungsnachricht an den Benutzer senden
                response_text = (
                    f"Ich habe folgende Informationen notiert:\n"
                    f"Name: {user_states[user_ip]['name']}\n"
                    f"E-Mail: {user_states[user_ip]['email']}\n"
                    f"Dienstleistung: {user_states[user_ip]['service']}\n"
                    f"Datum/Uhrzeit: {date_time_str}\n\n"
                    f"Ist das korrekt? Bitte antworten Sie mit 'Ja' oder 'Nein'."
                )
                user_states[user_ip]["state"] = "waiting_for_confirmation"
            except:
                response_text = "Ich konnte Datum und Uhrzeit nicht verstehen. Bitte versuchen Sie es in einem klaren Format wie 'Freitag, 15:00 Uhr' erneut."
                
        elif current_state == "waiting_for_confirmation":
            if user_message_lower in ["ja", "ja bitte", "korrekt"]:
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
            
            elif user_message_lower in ["nein", "abbrechen", "falsch"]:
                response_text = "Die Terminanfrage wurde abgebrochen. Falls Sie die Eingabe korrigieren möchten, beginnen Sie bitte erneut mit 'Termin vereinbaren'."
                user_states[user_ip]["state"] = "initial"
            
            else:
                response_text = "Bitte antworten Sie mit 'Ja' oder 'Nein'."
        
        return jsonify({"reply": response_text})

    except Exception as e:
        print(f"Ein Fehler ist aufgetreten: {e}")
        return jsonify({"error": "Interner Serverfehler"}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)


