#!/bin/bash
# AI Investment Arena – per Doppelklick starten.
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo "Erster Start: Ich richte alles ein (dauert 1–2 Minuten) …"
  python3 -m venv .venv || { echo "Python 3 fehlt. Bitte installieren: https://www.python.org/downloads/"; read -r; exit 1; }
  .venv/bin/pip install --upgrade pip -q
  .venv/bin/pip install -r requirements.txt -q
fi
echo "Team-Computer und Dashboard starten …"
echo "Dieses Fenster offen lassen – solange es offen ist, arbeitet das Team."
.venv/bin/python trader.py > data/trader.log 2>&1 &
TRADER=$!
trap 'kill $TRADER 2>/dev/null' EXIT
.venv/bin/python -m streamlit run app.py --browser.gatherUsageStats false --theme.base light --theme.primaryColor "#2563EB"
