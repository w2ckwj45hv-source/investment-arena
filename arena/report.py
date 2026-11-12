"""
Tagesbericht BERICHT.md – wird nach jedem Meeting neu geschrieben.
GitHub zeigt ihn als schöne Seite an, auch in der GitHub-App auf dem Handy.
"""
import json
from pathlib import Path

import pandas as pd

import config
from arena import explain
from arena.agents import AGENT_CLASSES
from arena.explain import company, de, eur

OUT = Path(__file__).resolve().parent.parent / "BERICHT.md"
WEEKDAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]


def de_day(d) -> str:
    d = pd.Timestamp(d)
    return f"{WEEKDAYS[d.weekday()]}, {d:%d.%m.%Y}"


def write(store, pid):
    p = store.portfolio(pid)
    initial = float(p["initial"])
    eq = store.q("SELECT * FROM equity WHERE portfolio_id = ? ORDER BY day", (pid,))
    meet = store.q("SELECT * FROM meetings WHERE portfolio_id = ? ORDER BY day DESC LIMIT 1", (pid,))
    pos = store.q("SELECT * FROM positions WHERE portfolio_id = ?", (pid,))
    tx = store.q("SELECT * FROM transactions WHERE portfolio_id = ? ORDER BY rowid DESC", (pid,))
    L = []

    if eq.empty or meet.empty:
        OUT.write_text("# KI-Team\n\nNoch kein Team-Meeting.\n", encoding="utf-8")
        return
    last = eq.iloc[-1]
    det = json.loads(meet.details[0])
    value, cash = float(last.value), float(last.cash)
    team_pct = (value / initial - 1) * 100
    idx_pct = (float(last.spx) / initial - 1) * 100

    L.append(f"# 📈 {p['name']}")
    L.append(f"*Stand: Börsenschluss am {de_day(last.day)} · Übungskonto bei Alpaca (Spielgeld)*\n")
    L.append(f"## {eur(value)}")
    L.append(f"**{eur(value - initial, True)} ({de(team_pct, 2, True)} %)** seit Start am {de_day(p['start_day'])} "
             f"mit {eur(initial)}\n")
    if len(eq) >= 2:
        text, good = explain.verdict(team_pct, idx_pct)
        L.append(f"> {'👍' if good else '👎'} {text}\n")
    else:
        L.append("> 🚀 Erster Handelstag. Der Vergleich mit dem Markt beginnt ab morgen.\n")

    invested = (value - cash) / value * 100 if value else 0
    L.append(f"In Aktien: **{invested:.0f} %** · Bargeld: **{eur(cash)}**\n")

    L.append("## 🗣️ Heute beschlossen")
    L.append("*Wird zur nächsten Börseneröffnung (15:30 Uhr deutscher Zeit) von Alpaca ausgeführt.*\n")
    orders = det.get("orders", [])
    if not orders:
        L.append("Keine Käufe oder Verkäufe – das Team ist mit dem Depot zufrieden.\n")
    for o in orders:
        buy = o["action"] == "KAUF"
        L.append(f"- {'🟢 **Kauft**' if buy else '🔴 **Verkauft**'} **{company(o['ticker'])}** · "
                 f"{o['shares']} Aktien · ca. {eur(o['value_eur'])}  \n  {explain.order_story(o, det)}")
    L.append("")

    L.append("## 👥 Was jeder im Team denkt\n")
    L.append("| | Agent | Meinung heute |")
    L.append("|---|---|---|")
    for c in AGENT_CLASSES:
        L.append(f"| {c.emoji} | **{c.name}**<br>{c.role} | {explain.agent_headline(c.key, det)} |")
    L.append("")
    if meet.summary[0]:
        L.append(f"**🤖 Protokoll von Claude:** {meet.summary[0]}\n")

    L.append("## 💼 Im Depot\n")
    if pos.empty:
        L.append("Noch keine Aktien – nur Bargeld.\n")
    else:
        prices = det.get("prices_eur", {})
        L.append("| Firma | Stück | Kaufpreis | Gewinn/Verlust |")
        L.append("|---|---:|---:|---:|")
        for r in pos.itertuples():
            now = prices.get(r.ticker)
            pl = f"{de((now / r.avg_cost_eur - 1) * 100, 1, True)} %" if now else "–"
            L.append(f"| {company(r.ticker)} | {r.shares} | {eur(r.avg_cost_eur)} | {pl} |")
        L.append("")

    L.append("## 📒 Tagebuch\n")
    for r in tx.head(15).itertuples():
        word = "🟢 Gekauft" if r.action == "KAUF" else "🔴 Verkauft"
        extra = f" · Ergebnis {eur(r.pnl_eur, True)}" if r.action == "VERKAUF" else ""
        L.append(f"- {de_day(r.day)}: {word} {r.shares} × {company(r.ticker)} zu {de(r.price_usd, 2)} $"
                 f" ({eur(r.value_eur)}){extra}")
    if tx.empty:
        L.append("- Noch keine ausgeführten Orders.")
    L.append("")

    les = store.q("SELECT day, text FROM lessons WHERE portfolio_id = ? ORDER BY day DESC LIMIT 6", (pid,))
    if not les.empty:
        L.append(f"## 🧠 Letzte Nachbesprechung ({de_day(les.day.iloc[0])})\n")
        for r in les[les.day == les.day.iloc[0]].itertuples():
            L.append(f"- {r.text}")
        L.append("")

    L.append("---\n*Echte Kurse, virtuelles Geld. Keine Anlageberatung.*")
    OUT.write_text("\n".join(L), encoding="utf-8")
