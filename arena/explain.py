"""
Übersetzt die Arbeit des Teams in einfache Sätze für das Dashboard.
Keine Fachbegriffe, keine Kürzel – Firmennamen statt Ticker.
"""
import config

ANALYSTS = ["market", "news", "value", "technical"]


def company(t: str) -> str:
    return config.UNIVERSE.get(t, (t,))[0]


def names(tickers, limit=3) -> str:
    tickers = list(tickers)[:limit]
    if not tickers:
        return ""
    words = [company(t) for t in tickers]
    return words[0] if len(words) == 1 else ", ".join(words[:-1]) + " und " + words[-1]


def de(x: float, decimals=1, sign=False) -> str:
    """Zahl im deutschen Format: 1.234,5"""
    s = f"{x:+,.{decimals}f}" if sign else f"{x:,.{decimals}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def eur(x: float, sign=False) -> str:
    s = f"{x:+,.0f} €" if sign else f"{x:,.0f} €"
    return s.replace(",", ".")


def _ranked(ops: dict, signal: str):
    items = [(t, o) for t, o in ops.items() if o["signal"] == signal]
    return [t for t, o in sorted(items, key=lambda x: -abs(x[1]["score"]))]


def agent_headline(key: str, det: dict) -> str:
    """Ein Satz pro Agent: Was denkt er heute?"""
    ops = det["opinions"].get(key, {})
    if key == "market":
        regime = det.get("regime", "")
        start = {"Bullenmarkt": "Die Börse ist im Aufwärtstrend.",
                 "Bärenmarkt": "Die Börse ist schwach – Vorsicht.",
                 }.get(regime, "Die Börse hat gerade keine klare Richtung.")
        strong = _ranked(ops, "KAUFEN")
        return start + (f" Besser als der Markt laufen {names(strong, 2)}." if strong else "")
    if key == "news":
        hot = [t for t, o in ops.items() if o["signal"] != "HALTEN"]
        if not hot:
            return "Keine Nachrichten, die den Kurs stark bewegen."
        good = [t for t in hot if ops[t]["signal"] == "KAUFEN"]
        bad = [t for t in hot if ops[t]["signal"] == "VERKAUFEN"]
        parts = []
        if good:
            parts.append(f"Gute Nachrichten bei {names(good, 2)}")
        if bad:
            parts.append(f"schlechte Nachrichten bei {names(bad, 2)}")
        s = " und ".join(parts)
        return s[0].upper() + s[1:] + "."
    if key == "value":
        cheap, pricey = _ranked(ops, "KAUFEN"), _ranked(ops, "VERKAUFEN")
        s = f"Gute Firmen zu fairem Preis: {names(cheap, 3)}." if cheap else "Findet gerade keine Schnäppchen."
        if pricey:
            s += f" Zu teuer: {names(pricey, 2)}."
        return s
    if key == "technical":
        up, down = _ranked(ops, "KAUFEN"), _ranked(ops, "VERKAUFEN")
        s = f"Die Charts zeigen nach oben bei {names(up, 3)}." if up else "Kaum Aufwärtstrends in den Charts."
        if down:
            s += f" Nach unten bei {names(down, 2)}."
        return s
    if key == "risk":
        lim = det.get("limits", {})
        s = f"Erlaubt heute höchstens {lim.get('max_invested', 0) * 100:.0f} % des Geldes in Aktien."
        if lim.get("stops"):
            s += f" Notbremse bei {names(lim['stops'])}: zu stark gefallen."
        return s
    if key == "pm":
        orders = det.get("orders", [])
        if not orders:
            return "Keine Änderungen heute – das Depot passt."
        b = sum(1 for o in orders if o["action"] == "KAUF")
        s = len(orders) - b
        parts = ([f"kauft {b} Aktie{'n' if b != 1 else ''}"] if b else []) + \
                ([f"verkauft {s}"] if s else [])
        return "Entscheidung: " + " und ".join(parts) + "."
    return ""


def order_story(order: dict, det: dict) -> str:
    """Warum hat das Team diese Order beschlossen? In einem Satz."""
    t = order["ticker"]
    if t in det.get("limits", {}).get("stops", []):
        return "Notbremse: Der Kurs ist zu weit unter seinen Höchststand gefallen. Verluste begrenzen."
    votes = {a: det["opinions"].get(a, {}).get(t) for a in ANALYSTS}
    votes = {a: o for a, o in votes.items() if o}
    pro = [a for a, o in votes.items() if o["signal"] == "KAUFEN"]
    con = [a for a, o in votes.items() if o["signal"] == "VERKAUFEN"]
    who = {"market": "Marcus", "news": "Nora", "value": "Victor", "technical": "Tessa"}
    def count(n, word):
        return f"{n} von {len(votes)} Analysten {'ist' if n == 1 else 'sind'} {word}."

    if order["action"] == "KAUF":
        if not pro:
            return "Leichte Aufstockung, weil das Team insgesamt positiv ist."
        best = max(pro, key=lambda a: votes[a]["confidence"])
        reason = votes[best]["reasons"][0] if votes[best]["reasons"] else ""
        return f"{count(len(pro), 'dafür')} {who[best]}: „{reason}“"
    if det.get("team_scores", {}).get(t, 0) > 0 or not con:
        return "Das Team mag die Aktie weiter, verkleinert aber die Position, damit das Risiko im Rahmen bleibt."
    best = max(con, key=lambda a: votes[a]["confidence"])
    reason = votes[best]["reasons"][0] if votes[best]["reasons"] else ""
    return f"{count(len(con), 'dagegen')} {who[best]}: „{reason}“"


def verdict(team_pct: float, index_pct: float) -> tuple:
    """Ein klarer Satz: Ist das Team besser als der Markt? Gibt (Text, gut?) zurück."""
    diff = team_pct - index_pct
    if abs(diff) < 0.5:
        return "Das Team liegt gleichauf mit dem Markt (S&P 500).", True
    if diff > 0:
        return f"Das Team ist {de(diff)} Prozentpunkte besser als der Markt (S&P 500: {de(index_pct, sign=True)} %).", True
    return f"Das Team liegt {de(-diff)} Prozentpunkte hinter dem Markt (S&P 500: {de(index_pct, sign=True)} %).", False
