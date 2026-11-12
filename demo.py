"""
Zeitraffer-Demo: lässt das Team das letzte Jahr nachspielen.

Braucht kein Konto und keinen Schlüssel. Lädt echte Kurse von Yahoo Finance,
handelt mit virtuellem Geld über den eingebauten Broker und schreibt am Ende
den Bericht BERICHT.md.

    python demo.py
"""
import warnings

warnings.filterwarnings("ignore")

from arena import report  # noqa: E402
from arena.engine import Simulation, new_portfolio  # noqa: E402
from arena.storage import DB_PATH, Store  # noqa: E402

DEMO_DB = DB_PATH.with_name("demo.db")


def main() -> int:
    DEMO_DB.unlink(missing_ok=True)  # jede Demo beginnt mit einem frischen Depot
    store = Store(DEMO_DB)
    pid = new_portfolio(store, "replay")
    days = Simulation(store, pid).run()
    eq = store.q("SELECT day, value, spx, equal_weight FROM equity WHERE portfolio_id = ? ORDER BY day", (pid,))
    if eq.empty:
        print("Keine Handelstage gefunden.")
        return 1
    first, last = eq.iloc[0], eq.iloc[-1]
    change = lambda col: (last[col] / first[col] - 1) * 100  # noqa: E731
    print(f"{days} Handelstage nachgespielt, {first.day} bis {last.day}")
    print(f"Team-Depot:              {change('value'):+.1f} %")
    print(f"S&P 500 zum Vergleich:   {change('spx'):+.1f} %")
    print(f"Alle Aktien gleich viel: {change('equal_weight'):+.1f} %")
    report.write(store, pid)
    print("Bericht geschrieben: BERICHT.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
