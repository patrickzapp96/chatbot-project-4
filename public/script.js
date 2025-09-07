const toggleBtn = document.getElementById("chat-toggle");
const chatWidget = document.getElementById("chat-widget");
const closeBtn = document.getElementById("chat-close");
const typingIndicator = document.getElementById("typing-indicator");
const chatInput = document.getElementById("chat-input").querySelector("input");

toggleBtn.addEventListener("click", () => {
    // Wenn der Chat geöffnet wird...
    if (chatWidget.style.display === "none") {
        chatWidget.style.display = "flex";
        toggleBtn.style.display = "none";
        
        // Füge die beiden Startnachrichten hinzu
        // Optional: Kurze Verzögerung für einen realistischeren Effekt
        setTimeout(() => {
            // Hinzufügen einer neuen Klasse 'bot-red-message' für die rote Farbe
            addMessage("Es werden keine personenbezogenen Daten gespeichert.", "bot", "bot-red-message");
            setTimeout(() => {
                // Hinzufügen einer neuen Klasse 'bot-red-message' für die rote Farbe
                addMessage("Terminanfragen hier möglich.", "bot", "bot-red-message");
                    setTimeout(() => {
                        addMessage("Wie kann ich Ihnen behilflich sein?", "bot");
                    }, 500); // 0.5 Sekunden Verzögerung 
            }, 500); // 0.5 Sekunden Verzögerung
        }, 300); // 0.3 Sekunden Verzögerung nach dem Öffnen
    }
});
closeBtn.addEventListener("click", () => {
    chatWidget.style.display = "none";
    toggleBtn.style.display = "flex";
});
chatInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
        sendMessage();
    }
});
async function sendMessage() {
    const input = document.getElementById("userMessage");
    const msg = input.value.trim();
    if (!msg) return;

    addMessage(msg, "user");
    input.value = "";

    typingIndicator.style.display = "block";

    try {
        const res = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: msg })
        });
        if (!res.ok) {
            throw new Error(`Serverantwort war nicht okay: ${res.status}`);
        }

        const data = await res.json();
        // Füge eine Verzögerung von 500ms (0,5 Sekunden) hinzu
        setTimeout(() => {
            addMessage(data.reply, "bot");
            typingIndicator.style.display = "none";
        }, 500);
    } catch (error) {
        console.error("Fehler beim Senden der Nachricht:", error);
        addMessage("Entschuldigung, ich kann gerade nicht antworten.", "bot");
    } finally {
        typingIndicator.style.display = "none";
    }
}

// Die addMessage-Funktion wurde erweitert, um eine optionale Klasse zu akzeptieren
function addMessage(text, sender, extraClass = null) {
    const chat = document.getElementById("chat-messages");
    const msgDiv = document.createElement("div");
    msgDiv.classList.add("message", sender);
    
    // Füge die zusätzliche Klasse hinzu, falls vorhanden
    if (extraClass) {
        msgDiv.classList.add(extraClass);
    }

    const avatar = document.createElement("div");
    avatar.classList.add("avatar");

    // Emojis als Avatar setzen
    if (sender === "user") {
        avatar.innerText = "🧍"; // Emoji für den Benutzer
    } else {
        avatar.innerText = "🤖"; // Emoji für den Bot
    }

    const bubble = document.createElement("div");
    bubble.classList.add("bubble"); // Wichtig: füge diese Klasse hinzu
    bubble.innerText = text;
    if (sender === "user") {
        msgDiv.appendChild(bubble);
        msgDiv.appendChild(avatar);
    } else {
        msgDiv.appendChild(avatar);
        msgDiv.appendChild(bubble);
    }

    chat.appendChild(msgDiv);
    chat.scrollTop = chat.scrollHeight;
}
