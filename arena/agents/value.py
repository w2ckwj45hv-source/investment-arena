"""3. Value Investor – denkt wie ein klassischer langfristiger Investor."""
from arena.agents.base import Agent, num


class ValueInvestor(Agent):
    key = "value"
    name = "Victor"
    role = "Value Investor"
    emoji = "💎"
    description = ("Sucht gute Unternehmen zu fairen Preisen: Bewertung (KGV, PEG), Wachstum, "
                   "Gewinnmargen, Schulden, freier Cashflow – und Qualität mit Rabatt.")

    def analyze(self, ctx, brain):
        for t in ctx.frames:
            f = ctx.fundamentals.get(t) or {}
            if not f:
                brain.post(self.opinion(t, 0, ["Keine Unternehmenskennzahlen verfügbar"]))
                continue
            s, why = 0.0, []
            fpe = num(f, "forwardPE")
            if fpe is not None and fpe > 0:
                if fpe < 15:
                    s += 0.3
                    why.append(f"Günstig bewertet: erwartetes KGV {fpe:.1f}")
                elif fpe < 25:
                    s += 0.15
                    why.append(f"Fair bewertet: erwartetes KGV {fpe:.1f}")
                elif fpe > 45:
                    s -= 0.25
                    why.append(f"Sehr teuer: erwartetes KGV {fpe:.1f}")
                elif fpe > 35:
                    s -= 0.1
                    why.append(f"Teuer: erwartetes KGV {fpe:.1f}")
            peg = num(f, "pegRatio") or num(f, "trailingPegRatio")
            if peg is not None and peg > 0:
                if peg < 1:
                    s += 0.2
                    why.append(f"PEG {peg:.2f}: Wachstum günstig zu haben")
                elif peg > 2.5:
                    s -= 0.15
                    why.append(f"PEG {peg:.2f}: Wachstum teuer bezahlt")
            g = num(f, "revenueGrowth")
            if g is not None:
                if g > 0.15:
                    s += 0.2
                    why.append(f"Starkes Umsatzwachstum ({g * 100:.0f} %)")
                elif g > 0.05:
                    s += 0.1
                    why.append(f"Solides Umsatzwachstum ({g * 100:.0f} %)")
                elif g < 0:
                    s -= 0.2
                    why.append(f"Umsatz schrumpft ({g * 100:.0f} %)")
            pm = num(f, "profitMargins")
            if pm is not None:
                if pm > 0.2:
                    s += 0.15
                    why.append(f"Hohe Gewinnmarge ({pm * 100:.0f} %)")
                elif pm < 0.05:
                    s -= 0.15
                    why.append(f"Niedrige Gewinnmarge ({pm * 100:.0f} %)")
            de = num(f, "debtToEquity")
            if de is not None and ctx.sectors.get(t) != "Finanzen":  # bei Banken nicht aussagekräftig
                if de < 50:
                    s += 0.1
                    why.append("Geringe Verschuldung")
                elif de > 150:
                    s -= 0.2
                    why.append(f"Hohe Verschuldung (Schulden/Eigenkapital {de / 100:.1f})")
            fcf, mcap = num(f, "freeCashflow"), num(f, "marketCap")
            if fcf and mcap:
                y = fcf / mcap
                if y > 0.04:
                    s += 0.15
                    why.append(f"Hohe Free-Cashflow-Rendite ({y * 100:.1f} %)")
                elif y < 0.01:
                    s -= 0.1
                    why.append(f"Niedrige Free-Cashflow-Rendite ({y * 100:.1f} %)")

            # Qualität mit Rabatt: gutes Unternehmen deutlich unter Jahreshoch
            dd = num(ctx.row(t), "drawdown252")
            if dd is not None:
                if dd < -0.25 and (pm or 0) > 0.1:
                    s += 0.2
                    why.append(f"Qualitätsunternehmen {dd * 100:.0f} % unter Jahreshoch – Rabatt")
                elif dd > -0.03 and (fpe or 0) > 35:
                    s -= 0.1
                    why.append("Teuer und nahe am Jahreshoch – wenig Sicherheitsmarge")
            brain.post(self.opinion(t, s, why or ["Kennzahlen ohne klare Aussage"]))
