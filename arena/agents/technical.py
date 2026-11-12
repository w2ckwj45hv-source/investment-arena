"""4. Technical Trader – liest Charts: Trends, Unterstützung/Widerstand, Momentum, Signale."""
from arena.agents.base import Agent, num


class TechnicalTrader(Agent):
    key = "technical"
    name = "Tessa"
    role = "Technical Trader"
    emoji = "📈"
    description = ("Analysiert Charts: gleitende Durchschnitte, RSI, MACD, Bollinger-Bänder, "
                   "Ausbrüche über Widerstände und Brüche von Unterstützungen.")

    def analyze(self, ctx, brain):
        for t in ctx.frames:
            r = ctx.row(t)
            c, s20, s50, s200 = (num(r, k) for k in ["close", "sma20", "sma50", "sma200"])
            if not all([c, s20, s50, s200]):
                brain.post(self.opinion(t, 0, ["Zu wenig Kursgeschichte für Chartanalyse"]))
                continue
            s, why = 0.0, []
            if c > s50:
                s += 0.2
                why.append("Kurs über der 50-Tage-Linie (mittelfristiger Aufwärtstrend)")
            else:
                s -= 0.2
                why.append("Kurs unter der 50-Tage-Linie (mittelfristiger Abwärtstrend)")
            s += 0.15 if s20 > s50 else -0.15
            if c > s200:
                s += 0.15
            else:
                s -= 0.15
                why.append("Kurs unter der 200-Tage-Linie")

            hist = num(r, "macd_hist")
            if hist is not None:
                prev = num(ctx.frames[t].iloc[ctx.i - 1], "macd_hist") if ctx.i > 0 else None
                if hist > 0 and prev is not None and hist > prev:
                    s += 0.15
                    why.append("MACD positiv und steigend (Momentum nimmt zu)")
                elif hist < 0 and prev is not None and hist < prev:
                    s -= 0.15
                    why.append("MACD negativ und fallend (Momentum nimmt ab)")

            rsi = num(r, "rsi")
            if rsi is not None:
                if rsi > 75:
                    s -= 0.25
                    why.append(f"RSI {rsi:.0f}: überkauft – Rücksetzer wahrscheinlich")
                elif rsi < 30:
                    if c > s200:
                        s += 0.25
                        why.append(f"RSI {rsi:.0f}: überverkauft im Aufwärtstrend – Kaufgelegenheit")
                    else:
                        why.append(f"RSI {rsi:.0f}: überverkauft, aber im Abwärtstrend")
                elif 50 <= rsi <= 70:
                    s += 0.05

            hi, lo, vr = num(r, "high20_prev"), num(r, "low20_prev"), num(r, "vol_ratio") or 1.0
            if hi and c > hi:
                bonus = 0.3 if vr > 1.3 else 0.15
                s += bonus
                why.append(f"Ausbruch über den 20-Tage-Widerstand ({hi:.2f} $)"
                           + (" mit hohem Volumen" if vr > 1.3 else ""))
            elif lo and c < lo:
                s -= 0.3
                why.append(f"Unterstützung bei {lo:.2f} $ gebrochen")
            elif hi and lo:
                why.append(f"Handelsspanne: Unterstützung {lo:.2f} $, Widerstand {hi:.2f} $")

            bu, bl = num(r, "bb_upper"), num(r, "bb_lower")
            if bu and c > bu:
                s -= 0.1
                why.append("Über dem oberen Bollinger-Band (überdehnt)")
            elif bl and c < bl and c > s200:
                s += 0.1
                why.append("Unter dem unteren Bollinger-Band im Aufwärtstrend")
            brain.post(self.opinion(t, s, why))
