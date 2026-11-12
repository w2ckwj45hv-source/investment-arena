"""Grundbaustein für alle Agenten."""
import math

from arena.brain import Opinion


def num(row, key):
    """Liest eine Zahl; gibt None zurück, wenn sie (noch) fehlt."""
    v = row.get(key) if hasattr(row, "get") else None
    if v is None:
        return None
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(v) else v


def clip(x, lo=-1.0, hi=1.0):
    return max(lo, min(hi, x))


def pct(x):
    return f"{x * 100:+.1f} %"


class Agent:
    key = ""
    name = ""
    role = ""
    emoji = ""
    description = ""

    def __init__(self):
        # Das eigene kleine Gehirn: Erinnerungen dieses Agenten
        self.memory = {"last_signal": {}}

    def opinion(self, ticker, score, reasons) -> Opinion:
        score = clip(score)
        signal = "KAUFEN" if score >= 0.2 else "VERKAUFEN" if score <= -0.2 else "HALTEN"
        confidence = int(round(1 + 9 * min(1.0, abs(score) / 0.8)))
        last = self.memory["last_signal"].get(ticker)
        if last and last != signal:
            reasons = reasons + [f"Meinungswechsel: vorher {last}, jetzt {signal}"]
        self.memory["last_signal"][ticker] = signal
        return Opinion(self.key, ticker, signal, round(score, 3), confidence, reasons)

    def analyze(self, ctx, brain):
        raise NotImplementedError
