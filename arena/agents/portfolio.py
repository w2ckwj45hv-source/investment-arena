"""
6. Portfolio Manager – der Kopf des Teams.

Hört alle Analysten an, gewichtet sie nach ihrem gelernten Vertrauen, legt Zielgewichte fest,
lässt sie vom Risk Manager prüfen und erteilt dann die konkreten Orders.
"""
import config
from arena.agents.base import Agent
from arena.broker import Order

ANALYSTS = ["market", "technical", "value", "news"]
NAMES = {"market": "Marcus", "technical": "Tessa", "value": "Victor", "news": "Nora", "risk": "Rita"}


def eur(x):
    return f"{x:,.0f} €".replace(",", ".")


class PortfolioManager(Agent):
    key = "pm"
    name = "Paul"
    role = "Portfolio Manager"
    emoji = "🎯"
    description = ("Führt das Team. Kombiniert alle Analysen gewichtet nach Vertrauen und "
                   "Erfahrung, entscheidet über Käufe und Verkäufe.")

    def team_score(self, ticker, brain):
        ops = brain.opinions_for(ticker)
        num_, den, parts = 0.0, 0.0, []
        for a in ANALYSTS:
            op = ops.get(a)
            if not op:
                continue
            base = config.PM["base_weights"][a] * brain.trust.get(a, 1.0)
            num_ += base * (op.confidence / 10) * op.score
            den += base
            parts.append(f"{NAMES[a]}: {op.signal} {op.confidence}/10")
        score = num_ / den if den else 0.0
        risk = ops.get("risk")
        if risk and risk.score < 0:
            score += risk.score * 0.15
        return score, parts

    def propose(self, ctx, brain, current: dict) -> dict:
        targets, self.scores = {}, {}
        lim = brain.risk_limits
        for t in ctx.frames:
            score, parts = self.team_score(t, brain)
            self.scores[t] = (score, parts)
            cw = current.get(t, 0.0)
            if score >= config.PM["buy_threshold"]:
                conviction = min(1.0, score / 0.45)
                targets[t] = max(lim["max_w"][t] * conviction, cw if cw <= lim["max_w"][t] else 0)
            elif score <= config.PM["sell_threshold"]:
                targets[t] = 0.0
            else:
                targets[t] = cw  # halten
        ranked = sorted(self.scores.items(), key=lambda kv: -kv[1][0])
        top = ", ".join(f"{t} {s:+.2f}" for t, (s, _) in ranked[:3])
        low = ", ".join(f"{t} {s:+.2f}" for t, (s, _) in ranked[-2:])
        brain.say(self.key, f"Ich habe alle Analysen gehört. Stärkste Team-Scores: {top}. "
                            f"Schwächste: {low}. Mein Vorschlag geht an Rita zur Prüfung.")
        return targets

    def make_orders(self, targets: dict, current: dict, ctx, brain) -> list:
        value = ctx.depot.value(ctx.prices, ctx.fx)
        sells, buys, lines = [], [], []
        for t, tw in targets.items():
            cw = current.get(t, 0.0)
            diff = tw - cw
            held = ctx.depot.positions.get(t)
            closing = tw == 0 and held
            if not closing and abs(diff) < config.PM["min_trade_pct"]:
                continue
            price_eur = ctx.prices[t] / ctx.fx
            score, parts = self.scores[t]
            why = f"Team-Score {score:+.2f} ({'; '.join(parts)})"
            if diff > 0:
                n = int(diff * value / price_eur)
                if n > 0:
                    buys.append(Order(t, "KAUF", n, why))
                    lines.append(f"🟢 KAUFE {n} × {t} für ca. {eur(n * price_eur)} → Ziel {tw * 100:.1f} % des Depots. {why}")
            else:
                n = held.shares if closing else int(-diff * value / price_eur)
                n = min(n, held.shares) if held else 0
                if n > 0:
                    if t in brain.risk_limits.get("stops", []):
                        why = "Stop-Loss von Rita. " + why
                    elif tw > 0:
                        why = "Position verkleinern (Risiko-Grenze oder geringere Überzeugung). " + why
                    sells.append(Order(t, "VERKAUF", n, why))
                    lines.append(f"🔴 VERKAUFE {n} × {t} für ca. {eur(n * price_eur)} → Ziel {tw * 100:.1f} %. {why}")
        if lines:
            brain.say(self.key, "Meine Entscheidungen (Ausführung zum Eröffnungskurs am nächsten Handelstag):\n"
                      + "\n".join(f"- {x}" for x in lines))
        else:
            brain.say(self.key, "Heute keine Änderungen – das Depot passt zu unserer Einschätzung. Wir halten.")
        return sells + buys

    def analyze(self, ctx, brain):  # der PM analysiert nicht selbst, er entscheidet
        pass
