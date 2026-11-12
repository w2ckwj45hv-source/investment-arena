"""
2. News Analyst – bewertet Nachrichten und Marktstimmung.

Zwei Werkzeuge:
- Schlagzeilen lesen (im Live-Betrieb): positive und negative Signalwörter zählen
- Ereignis-Erkennung (immer): starke Kurssprünge mit hohem Volumen deuten auf wichtige
  Nachrichten hin – deren Richtung hält oft noch einige Tage an
"""
from arena.agents.base import Agent, clip, num, pct

POSITIVE = ["beat", "beats", "surge", "soar", "record", "upgrade", "raises", "raised", "strong",
            "growth", "rally", "jump", "partnership", "buyback", "outperform", "gain", "wins",
            "approval", "approved", "boost", "bullish", "tops", "expands", "breakthrough", "rises"]
NEGATIVE = ["miss", "misses", "plunge", "crash", "downgrade", "cut", "lawsuit", "probe",
            "investigation", "recall", "weak", "falls", "drop", "slump", "warning", "warns",
            "layoff", "fine", "ban", "tariff", "sell-off", "selloff", "decline", "bearish",
            "slows", "loses", "fraud", "delay", "sinks", "tumble"]

ALIASES = {"AAPL": ["apple", "iphone"], "MSFT": ["microsoft", "azure"], "NVDA": ["nvidia"],
           "AMZN": ["amazon", "aws"], "GOOGL": ["alphabet", "google"], "META": ["meta", "facebook"],
           "TSLA": ["tesla", "musk"], "JPM": ["jpmorgan", "jpm"], "JNJ": ["johnson"],
           "XOM": ["exxon"]}


def headline_tone(title: str) -> int:
    t = title.lower()
    return sum(w in t for w in POSITIVE) - sum(w in t for w in NEGATIVE)


class NewsAnalyst(Agent):
    key = "news"
    name = "Nora"
    role = "News Analyst"
    emoji = "📰"
    description = ("Liest Schlagzeilen und erkennt Nachrichten-Ereignisse an auffälligen "
                   "Kurssprüngen mit hohem Handelsvolumen.")

    def analyze(self, ctx, brain):
        for t in ctx.frames:
            s, why = 0.0, []
            # Ereignis-Erkennung der letzten 5 Tage
            hist = ctx.hist(t, 5)
            for age, (_, r) in enumerate(reversed(list(hist.iterrows()))):
                ret, vr = num(r, "ret_1d"), num(r, "vol_ratio")
                if ret is None or vr is None:
                    continue
                if abs(ret) > 0.03 and vr > 1.8:
                    decay = 1 - age * 0.18
                    s += clip(ret / 0.08) * 0.7 * decay
                    when = "heute" if age == 0 else f"vor {age} Tag(en)"
                    why.append(f"Nachrichten-Ereignis {when}: Kurs {pct(ret)} bei "
                               f"{vr:.1f}-fachem Volumen")
                    break

            # Schlagzeilen (nur im Live-Betrieb verfügbar)
            if ctx.news is not None:
                names = ALIASES.get(t, [t.lower()])
                # nur Schlagzeilen, die das Unternehmen selbst nennen
                relevant = [n for n in ctx.news.get(t, []) if any(a in n["title"].lower() for a in names)]
                tones = [(n["title"], headline_tone(n["title"])) for n in relevant[:8]]
                if tones:
                    total = sum(x for _, x in tones)
                    s += clip(total / max(3, len(tones))) * 0.6
                    pos = sum(1 for _, x in tones if x > 0)
                    neg = sum(1 for _, x in tones if x < 0)
                    why.append(f"{len(tones)} Schlagzeilen gelesen: {pos} positiv, {neg} negativ")
                    for title, x in sorted(tones, key=lambda z: -abs(z[1]))[:2]:
                        if x:
                            why.append(f"„{title[:90]}“ ({'positiv' if x > 0 else 'negativ'})")
            if not why:
                why.append("Keine auffälligen Nachrichten")
            brain.post(self.opinion(t, s, why))
