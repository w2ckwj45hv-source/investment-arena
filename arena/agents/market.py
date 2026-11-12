"""1. Market Analyst – beurteilt die Gesamtlage des Marktes und die relative Stärke jeder Aktie."""
import math

from arena.agents.base import Agent, clip, num, pct


class MarketAnalyst(Agent):
    key = "market"
    name = "Marcus"
    role = "Market Analyst"
    emoji = "🌍"
    description = ("Beobachtet den Gesamtmarkt (S&P 500): Trend, Schwung und Nervosität. "
                   "Bewertet, ob eine Aktie stärker oder schwächer als der Markt läuft.")

    def analyze(self, ctx, brain):
        b = ctx.bench_row()
        m, why = 0.0, []
        close, sma50, sma200 = num(b, "close"), num(b, "sma50"), num(b, "sma200")
        if close and sma200:
            if close > sma200:
                m += 0.35
                why.append("S&P 500 liegt über der 200-Tage-Linie (langfristiger Aufwärtstrend)")
            else:
                m -= 0.35
                why.append("S&P 500 liegt unter der 200-Tage-Linie (langfristiger Abwärtstrend)")
        if sma50 and sma200:
            m += 0.2 if sma50 > sma200 else -0.2
        r60 = num(b, "ret_60d")
        if r60 is not None:
            m += clip(r60 / 0.10) * 0.25
            why.append(f"Markt in 3 Monaten {pct(r60)}")
        vol, vol_med = num(b, "vol20"), num(b, "vol_median")
        if vol and vol_med:
            if vol > 1.4 * vol_med:
                m -= 0.2
                why.append(f"Der Markt ist nervös (Schwankung {vol * 100:.0f} % p.a., normal {vol_med * 100:.0f} %)")
            elif vol < 0.9 * vol_med:
                m += 0.05
                why.append("Der Markt ist ruhig")
        m = clip(m)
        regime = "Bullenmarkt" if m >= 0.3 else "Bärenmarkt" if m <= -0.3 else "Neutral"
        brain.market_view = {"regime": regime, "score": round(m, 2), "reasons": why}
        brain.say(self.key, f"Marktlage heute: **{regime}** (Markt-Score {m:+.2f}). " + "; ".join(why) + ".")

        br60, br120 = num(b, "ret_60d") or 0.0, num(b, "ret_120d") or 0.0
        for t in ctx.frames:
            r = ctx.row(t)
            s60, s120 = num(r, "ret_60d"), num(r, "ret_120d")
            if s60 is None or s120 is None:
                brain.post(self.opinion(t, 0, ["Zu wenig Kursgeschichte"]))
                continue
            rs60, rs120 = s60 - br60, s120 - br120
            score = math.tanh(rs60 / 0.10) * 0.45 + math.tanh(rs120 / 0.20) * 0.30 + m * 0.25
            reasons = [f"Relative Stärke zum Markt: 3 Monate {pct(rs60)}, 6 Monate {pct(rs120)}",
                       f"Rückenwind/Gegenwind durch Marktlage ({regime})"]
            vr, r20 = num(r, "vol_ratio"), num(r, "ret_20d")
            if vr and r20 and r20 > 0 and vr > 1.2:
                score += 0.05
                reasons.append("Steigende Kurse mit erhöhtem Volumen – Käufer sind aktiv")
            brain.post(self.opinion(t, score, reasons))
