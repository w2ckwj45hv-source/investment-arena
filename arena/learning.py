"""
Lernfunktion: die regelmäßige Nachbesprechung des Teams.

Alle 20 Handelstage schaut sich das Team an, was aus früheren Signalen geworden ist:
- War ein KAUFEN-Signal richtig? (Aktie lief danach besser als der Markt)
- War ein VERKAUFEN-Signal richtig? (Aktie lief danach schlechter als der Markt)

Analysten, die oft richtig liegen, bekommen mehr Vertrauen – der Portfolio Manager hört
ihnen künftig stärker zu. Wer oft danebenliegt, verliert Gewicht. So verbessert sich das
Team aus eigenen Ergebnissen, statt zufällig zu handeln.
"""
import config
from arena.explain import company, de

L = config.LEARNING
ANALYSTS = ["market", "technical", "value", "news"]
NAMES = {"market": "Marcus (Market)", "technical": "Tessa (Technical)", "value": "Victor (Value)",
         "news": "Nora (News)"}


def review(store, pid, i, dates, close, bench_close, brain):
    h = L["horizon_days"]
    if i < h:
        return []
    cutoff = dates[i - h].strftime("%Y-%m-%d")
    ops = store.q("SELECT id, day, agent, ticker, signal, confidence FROM opinions "
                  "WHERE portfolio_id = ? AND evaluated = 0 AND day <= ?", (pid, cutoff))
    if ops.empty:
        return []
    pos = {d.strftime("%Y-%m-%d"): k for k, d in enumerate(dates)}
    rows, results = [], []
    for r in ops.itertuples():
        k0 = pos.get(r.day)
        if k0 is None or k0 + h > i:
            continue
        ret = close[r.ticker].iloc[k0 + h] / close[r.ticker].iloc[k0] - 1
        bret = bench_close.iloc[k0 + h] / bench_close.iloc[k0] - 1
        excess = float(ret - bret)
        correct = None
        if r.signal == "KAUFEN":
            correct = int(excess > 0)
        elif r.signal == "VERKAUFEN":
            correct = int(excess < 0)
        rows.append((correct, excess, r.id))
        if correct is not None:
            results.append((r.agent, correct, r.confidence, excess, r.signal))
    store.many("UPDATE opinions SET evaluated = 1, correct = ?, excess = ? WHERE id = ?", rows)

    day = dates[i].strftime("%Y-%m-%d")
    lessons = []
    for a in ANALYSTS:
        mine = [x for x in results if x[0] == a]
        if len(mine) < 10:
            continue
        w = sum(c for _, _, c, _, _ in mine)
        hit = sum(ok * c for _, ok, c, _, _ in mine) / w
        buys = [e for *_, e, s in mine if s == "KAUFEN"]
        old = brain.trust.get(a, 1.0)
        new = min(L["trust_max"], max(L["trust_min"], old * (1 + L["learning_rate"] * (hit - 0.5) * 2)))
        brain.trust[a] = new
        store.exec("INSERT INTO trust VALUES (?, ?, ?, ?, ?, ?)", (pid, day, a, new, hit, len(mine)))
        trend = "↑ mehr Vertrauen" if new > old + 1e-3 else "↓ weniger Vertrauen" if new < old - 1e-3 else "→ unverändert"
        text = (f"{NAMES[a]}: {hit * 100:.0f} % der Signale richtig ({len(mine)} Signale bewertet). "
                f"Vertrauen {de(old, 2)} → {de(new, 2)} ({trend}).")
        if buys:
            avg = sum(buys) / len(buys)
            text += (f" Seine Kaufempfehlungen liefen im Schnitt {de(abs(avg) * 100)} % "
                     f"{'besser' if avg >= 0 else 'schlechter'} als der Markt.")
        lessons.append((pid, day, a, text))

    trades = store.q("SELECT ticker, pnl_eur FROM transactions WHERE portfolio_id = ? AND action = 'VERKAUF' "
                     "AND day > ? AND day <= ?", (pid, dates[max(0, i - L["review_every_days"])].strftime("%Y-%m-%d"), day))
    if not trades.empty:
        best, worst = trades.loc[trades.pnl_eur.idxmax()], trades.loc[trades.pnl_eur.idxmin()]
        won = (trades.pnl_eur > 0).mean()
        eur = lambda x: f"{x:+,.0f} €".replace(",", ".")  # noqa: E731
        lessons.append((pid, day, "pm",
                        f"Paul (PM): {len(trades)} Verkäufe, davon {won * 100:.0f} % mit Gewinn. "
                        f"Bester: {company(best.ticker)} {eur(best.pnl_eur)}, schlechtester: {company(worst.ticker)} {eur(worst.pnl_eur)}."))
    if lessons:
        store.many("INSERT INTO lessons VALUES (?, ?, ?, ?)", lessons)
        brain.lessons = [x[3] for x in lessons]
    return lessons
