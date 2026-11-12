# Anleitung: Das KI-Team in die Cloud bringen

Danach arbeitet das Team **jeden Börsentag von selbst**. Kein Computer muss an sein.
Du brauchst etwa **20 Minuten**, einmalig. Am besten am Computer mit dem Browser **Google Chrome**.

---

## Teil A – Alpaca: dein Übungsdepot (Spielgeld)

1. Öffne **https://app.alpaca.markets/signup** und registriere dich mit E-Mail und Passwort.
   Bestätige die E-Mail.
2. Nach dem Einloggen: Achte darauf, dass oben links **„Paper“** (Übungskonto) ausgewählt ist –
   **nicht** „Live“.
3. *(Optional)* Das Übungskonto startet normalerweise mit 100.000 $. Wenn du lieber mit etwa
   100.000 € starten willst: Falls Alpaca beim Zurücksetzen des Paper-Kontos einen Betrag anbietet,
   trage **112.000** ein (≈ 100.000 €).
4. Suche auf der Startseite den Bereich **„API Keys“** und klicke **„Generate New Keys“**
   (oder „Regenerate“).
5. Es erscheinen zwei Schlüssel: **Key** und **Secret**.
   **Kopiere beide sofort** in eine Notiz – das Secret wird nur dieses eine Mal angezeigt.

---

## Teil B – GitHub: hier wohnt und arbeitet das Team

### 1. Konto anlegen und eine eigene Kopie erstellen
1. Öffne **https://github.com/signup** und registriere dich (falls du noch kein Konto hast).
2. Öffne die Seite dieses Projekts und klicke oben rechts auf den grünen Knopf **„Use this template“**
   → **„Create a new repository“**.
3. Repository name: **ai-investment-arena**
4. Wähle **Private** (nur du kannst es sehen). Das Team speichert dort später dein Übungsdepot.
5. Klicke **„Create repository“**. Die tägliche Automatik ist in der Kopie schon enthalten.

### 2. Die Alpaca-Schlüssel sicher hinterlegen
1. Im Repository oben auf **„Settings“** klicken.
2. Links: **„Secrets and variables“** → **„Actions“**.
3. **„New repository secret“**:
   - Name: `ALPACA_KEY_ID` — Secret: *dein Alpaca-Key* → **„Add secret“**
4. Nochmal **„New repository secret“**:
   - Name: `ALPACA_SECRET_KEY` — Secret: *dein Alpaca-Secret* → **„Add secret“**

Die Schlüssel sind dort verschlüsselt. Niemand kann sie lesen – auch nicht in den Dateien.

### 3. Schreibrecht geben (damit das Team sein Gedächtnis speichern kann)
1. **Settings** → links **„Actions“** → **„General“**.
2. Ganz unten bei **„Workflow permissions“**: **„Read and write permissions“** wählen → **„Save“**.

### 4. Das Team zum ersten Mal starten
1. Oben auf **„Actions“** klicken.
2. Links **„KI-Team Tagesmeeting“** wählen.
3. Rechts **„Run workflow“** → grüner Knopf **„Run workflow“**.
4. Nach 2–4 Minuten erscheint ein **grüner Haken ✅**. Fertig!

Auf der Startseite deines Repositorys gibt es jetzt die Datei **BERICHT.md** – das ist dein Tagesbericht.

---

## Ab jetzt läuft alles von selbst

| Wann (deutsche Zeit) | Was passiert |
|---|---|
| Mo–Fr gegen **22:45 Uhr** (Sommerzeit 23:45 Uhr) | Das Team hält sein Meeting und schickt die Orders an Alpaca |
| Am nächsten Tag **15:30 Uhr** | Die Börse öffnet, Alpaca führt die Käufe und Verkäufe aus |
| Alle 20 Handelstage | Nachbesprechung: Das Team lernt aus seinen Ergebnissen |

**Nachsehen – auch auf dem Handy:**
- **Tagesbericht:** github.com → dein Repository → **BERICHT.md**
  (oder in der kostenlosen **GitHub-App**)
- **Depot und alle Orders:** **app.alpaca.markets** im Browser (Paper-Konto)

---

## Falls etwas nicht klappt

- **Roter Haken ❌ bei „Actions“**: Klick darauf und dann auf „Team-Meeting“ – dort steht auf Deutsch,
  was fehlt. Meistens ist ein Schlüssel falsch kopiert. GitHub schickt dir dann auch eine E-Mail.
- **Feiertag in den USA**: Das Team erkennt das und macht an dem Tag einfach nichts.
- **GitHub pausiert die Automatik** (kann nach langer Zeit ohne Änderungen passieren):
  Du bekommst eine E-Mail. Unter „Actions“ auf **„Enable workflow“** klicken.

---

*Echte Kurse, virtuelles Geld. Keine Anlageberatung.*
