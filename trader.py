"""
Der Team-Computer: läuft im Hintergrund und lässt das Team in Echtzeit arbeiten.

Jede Minute schaut er auf die Uhr der New Yorker Börse:
- Börse öffnet  → die Orders aus dem letzten Meeting werden zum echten Eröffnungskurs ausgeführt
- Börse schließt → das Team hält sein Meeting und beschließt die Orders für den nächsten Tag
- War der Computer aus, holt er verpasste Handelstage beim nächsten Start nach

Wird automatisch von Start.command gestartet.
"""
import json
import time
import traceback
import warnings
from datetime import datetime
from pathlib import Path

warnings.filterwarnings("ignore")

from arena.engine import Simulation, market_open_now, ny_now  # noqa: E402
from arena.storage import Store  # noqa: E402

STATUS = Path(__file__).resolve().parent / "data" / "trader_status.json"
RETRY_MINUTES = 30


def write_status(text: str):
    STATUS.write_text(json.dumps({"time": datetime.now().isoformat(timespec="seconds"), "text": text},
                                 ensure_ascii=False), encoding="utf-8")


def tick(store: Store, last_try: dict) -> str:
    ports = store.q("SELECT * FROM portfolios WHERE mode IN ('live', 'alpaca')")
    if ports.empty:
        return "Wartet auf ein Depot."
    ny = ny_now()
    msgs = []
    for p in ports.itertuples():
        # Börse offen: offene Orders zum Eröffnungskurs ausführen
        if p.mode == "live" and market_open_now():
            pend = store.q("SELECT COUNT(*) n FROM pending_orders WHERE portfolio_id = ?", (p.id,)).n[0]
            if pend:
                n = Simulation(store, p.id, refresh=True).execute_at_open()
                if n:
                    msgs.append(f"{n} Order(s) zur Börseneröffnung ausgeführt")
        # Nach Börsenschluss (oder verpasste Tage): Team-Meeting
        closed_today = ny.weekday() < 5 and (ny.hour, ny.minute) >= (16, 30)
        behind = p.last_day is None or p.last_day < ny.strftime("%Y-%m-%d")
        due = closed_today or (p.last_day or "") < _last_weekday(ny)
        if behind and due and time.time() - last_try.get(p.id, 0) > RETRY_MINUTES * 60:
            last_try[p.id] = time.time()
            n = Simulation(store, p.id, refresh=True).run()
            if n:
                msgs.append(f"Team-Meeting abgehalten ({n} Handelstag(e))")
    return "; ".join(msgs) or ("Börse geöffnet – Team beobachtet den Markt." if market_open_now()
                                else "Börse geschlossen – Team wartet auf den nächsten Handelstag.")


def _last_weekday(ny) -> str:
    """Letzter Werktag vor heute (für verpasste Meetings, z. B. nach dem Wochenende)."""
    import pandas as pd
    d = pd.Timestamp(ny.date()) - pd.tseries.offsets.BDay(1)
    return d.strftime("%Y-%m-%d")


def main():
    store, last_try = Store(), {}
    print("Team-Computer läuft. Fenster offen lassen.")
    while True:
        try:
            write_status(tick(store, last_try))
        except Exception as e:
            write_status(f"Fehler: {e.__class__.__name__}: {e}")
            traceback.print_exc()
        time.sleep(60)


if __name__ == "__main__":
    main()
