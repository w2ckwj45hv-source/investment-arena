"""
Das Team-Gehirn: der gemeinsame Ort, an dem die 6 Agenten zusammenarbeiten.

Jeder Agent hat sein eigenes kleines Gehirn (eigene Logik, eigene Erinnerungen).
Hier im Team-Gehirn kommen alle Gedanken zusammen:

- Whiteboard: alle Analysen des heutigen Tages, für jeden Agenten sichtbar
- Marktlage und Risiko-Grenzen, die alle beachten
- Vertrauen: wie stark der Portfolio Manager jedem Analysten zuhört (wird gelernt)
- Lektionen aus früheren Nachbesprechungen
- Protokoll des Team-Meetings (wer hat was gesagt)
"""
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd


@dataclass
class Opinion:
    agent: str
    ticker: str
    signal: str          # KAUFEN / HALTEN / VERKAUFEN
    score: float         # -1 (stark verkaufen) … +1 (stark kaufen)
    confidence: int      # 1 … 10
    reasons: list


@dataclass
class DayContext:
    """Alles, was das Team an einem Handelstag weiß – und nichts aus der Zukunft."""
    day: pd.Timestamp
    i: int                       # Position des Tages in den Datenreihen
    frames: dict                 # ticker -> DataFrame mit Kennzahlen
    bench: pd.DataFrame          # S&P 500 mit Kennzahlen
    fundamentals: dict
    news: Optional[dict]         # nur im Live-Betrieb am aktuellen Tag
    depot: object
    prices: dict                 # Schlusskurse in USD
    fx: float
    cooldown: dict               # ticker -> Index des Tages, ab dem wieder gekauft werden darf
    sectors: dict

    def row(self, ticker) -> pd.Series:
        return self.frames[ticker].iloc[self.i]

    def hist(self, ticker, n) -> pd.DataFrame:
        return self.frames[ticker].iloc[max(0, self.i - n + 1): self.i + 1]

    def bench_row(self) -> pd.Series:
        return self.bench.iloc[self.i]


@dataclass
class TeamBrain:
    trust: dict
    lessons: list = field(default_factory=list)
    whiteboard: dict = field(default_factory=dict)    # agent -> {ticker: Opinion}
    market_view: dict = field(default_factory=dict)
    risk_limits: dict = field(default_factory=dict)
    transcript: list = field(default_factory=list)    # [(agent_key, text)]

    def new_day(self):
        self.whiteboard, self.market_view, self.risk_limits, self.transcript = {}, {}, {}, []

    def post(self, op: Opinion):
        self.whiteboard.setdefault(op.agent, {})[op.ticker] = op

    def say(self, agent_key: str, text: str):
        self.transcript.append((agent_key, text))

    def opinions_for(self, ticker) -> dict:
        return {a: ops[ticker] for a, ops in self.whiteboard.items() if ticker in ops}

    def all_opinions(self):
        for ops in self.whiteboard.values():
            yield from ops.values()
