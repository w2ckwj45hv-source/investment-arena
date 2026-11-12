"""
Tägliches Team-Meeting in der Cloud (wird von GitHub jeden Abend automatisch gestartet).

1. Holt die neuesten Kurse und Nachrichten
2. Gleicht das Depot mit dem Alpaca-Übungskonto ab
3. Die 6 Agenten halten ihr Meeting und schicken die Orders an Alpaca
4. Schreibt den Tagesbericht BERICHT.md
"""
import os
import sys
import warnings

warnings.filterwarnings("ignore")

from arena import alpaca, report  # noqa: E402
from arena.engine import Simulation, new_portfolio  # noqa: E402
from arena.storage import Store  # noqa: E402


def main() -> int:
    if not alpaca.configured():
        print("FEHLER: Die Alpaca-Schlüssel fehlen. Bitte in GitHub unter Settings → Secrets eintragen "
              "(ALPACA_KEY_ID und ALPACA_SECRET_KEY).")
        return 1
    store = Store()
    ports = store.q("SELECT id FROM portfolios WHERE mode = 'alpaca' ORDER BY id")
    if ports.empty:
        pid = new_portfolio(store, "alpaca", name=os.environ.get("DEPOT_NAME") or "Team-Depot")
        print("Neues Depot angelegt.")
    else:
        pid = int(ports.id.iloc[0])
    n = Simulation(store, pid, refresh=True).run()
    print("Team-Meeting abgehalten." if n else "Für den letzten Handelstag wurde schon entschieden (oder Feiertag).")
    report.write(store, pid)
    print("Bericht geschrieben: BERICHT.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
