"""
5. Risk Manager – die Sicherung des Teams.

Arbeitet mit festen Regeln (siehe config.RISK), die niemand im Team aushebeln kann:
- maximale Größe einer Position (kleiner bei stark schwankenden Aktien)
- maximaler Anteil einer Branche
- Mindest-Bargeld und maximaler Investitionsgrad je nach Marktlage
- Trailing-Stop-Loss mit Sperrfrist
"""
from collections import defaultdict

import config
from arena.agents.base import Agent, num

R = config.RISK


class RiskManager(Agent):
    key = "risk"
    name = "Rita"
    role = "Risk Manager"
    emoji = "🛡️"
    description = ("Setzt die Grenzen: Positionsgröße nach Volatilität, Branchen-Limits, "
                   "Investitionsgrad nach Marktlage und Stop-Loss. Hat ein Vetorecht.")

    def analyze(self, ctx, brain):
        regime = brain.market_view.get("regime", "Neutral")
        max_invested = min(R["max_invested"][regime], 1 - R["min_cash"])
        max_w, stops = {}, []
        for t in ctx.frames:
            r = ctx.row(t)
            vol = num(r, "vol20") or 0.4
            max_w[t] = round(min(R["max_position"], R["vol_budget"] / max(vol, 0.05)), 4)
            s, why = 0.0, [f"Schwankung {vol * 100:.0f} % p.a. → maximal {max_w[t] * 100:.1f} % des Depots"]
            if vol > 0.5:
                s -= 0.3
                why.append("Sehr hohe Schwankung")
            elif vol > 0.35:
                s -= 0.1
            dd = num(r, "drawdown252")
            if dd is not None and dd < -0.3:
                s -= 0.2
                why.append(f"{dd * 100:.0f} % unter Jahreshoch")
            pos = ctx.depot.positions.get(t)
            if pos:
                drop = ctx.prices[t] / pos.peak_close - 1
                if drop <= -R["trailing_stop"]:
                    stops.append(t)
                    s = -1.0
                    why.append(f"STOP-LOSS: {drop * 100:.1f} % unter dem Höchststand seit Kauf")
                else:
                    why.append(f"Abstand zum Stop-Loss: {(drop + R['trailing_stop']) * 100:.1f} Prozentpunkte")
            if ctx.cooldown.get(t, -1) > ctx.i:
                why.append("Gesperrt nach Stop-Loss (Sperrfrist läuft)")
            brain.post(self.opinion(t, s, why))

        brain.risk_limits = {"max_invested": max_invested, "max_w": max_w, "stops": stops}
        text = (f"Bei einem {regime} erlaube ich höchstens {max_invested * 100:.0f} % Investitionsgrad, "
                f"maximal {R['max_position'] * 100:.0f} % pro Aktie und {R['max_sector'] * 100:.0f} % pro Branche.")
        if stops:
            text += " ⚠️ Stop-Loss ausgelöst bei: " + ", ".join(stops) + " – diese werden verkauft."
        brain.say(self.key, text)

    def review(self, targets: dict, current: dict, ctx, brain) -> dict:
        """Prüft die Zielgewichte des Portfolio Managers und korrigiert sie, falls nötig (Veto)."""
        lim = brain.risk_limits
        out, vetoes = dict(targets), []
        for t, w in list(out.items()):
            if t in lim["stops"] and w > 0:
                out[t] = 0.0
                vetoes.append(f"{t}: Stop-Loss – Position wird geschlossen")
            elif ctx.cooldown.get(t, -1) > ctx.i and w > current.get(t, 0):
                out[t] = current.get(t, 0)
                vetoes.append(f"{t}: Kauf abgelehnt, Sperrfrist nach Stop-Loss")
            elif w > lim["max_w"][t] + 1e-9:
                out[t] = lim["max_w"][t]
                vetoes.append(f"{t}: Position auf {lim['max_w'][t] * 100:.1f} % begrenzt")

        by_sector = defaultdict(float)
        for t, w in out.items():
            by_sector[ctx.sectors[t]] += w
        for sec, total in by_sector.items():
            if total > R["max_sector"] + 1e-9:
                f = R["max_sector"] / total
                for t in out:
                    if ctx.sectors[t] == sec:
                        out[t] *= f
                vetoes.append(f"Branche {sec}: {total * 100:.0f} % → auf {R['max_sector'] * 100:.0f} % reduziert")

        total = sum(out.values())
        if total > lim["max_invested"] + 1e-9:
            f = lim["max_invested"] / total
            out = {t: w * f for t, w in out.items()}
            vetoes.append(f"Investitionsgrad {total * 100:.0f} % → auf {lim['max_invested'] * 100:.0f} % reduziert")

        if vetoes:
            brain.say(self.key, "Veto / Korrekturen: " + "; ".join(vetoes) + ".")
        else:
            brain.say(self.key, "Alle Vorschläge liegen innerhalb meiner Grenzen. Freigegeben ✅")
        brain.risk_limits["vetoes"] = vetoes
        return out
