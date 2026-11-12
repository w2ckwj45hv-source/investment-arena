"""
Virtueller Broker: führt Orders mit virtuellem Geld aus – wie ein echter Online-Broker,
nur ohne echtes Geld.

- Depot in Euro, Aktien werden in US-Dollar gehandelt (Wechselkurs wird umgerechnet)
- Gebühren und Slippage (etwas schlechterer Kurs als angezeigt)
- nur ganze Aktien
"""
from dataclasses import dataclass, field

import config


@dataclass
class Position:
    shares: int
    avg_cost_eur: float      # durchschnittlicher Kaufpreis pro Aktie in Euro
    peak_close: float        # höchster Schlusskurs (USD) seit dem Kauf – für den Stop-Loss
    entry_day: str


@dataclass
class Order:
    ticker: str
    action: str              # "KAUF" oder "VERKAUF"
    shares: int
    reason: str = ""


@dataclass
class Depot:
    cash: float
    positions: dict = field(default_factory=dict)   # ticker -> Position

    def value(self, prices_usd: dict, fx: float) -> float:
        return self.cash + self.invested(prices_usd, fx)

    def invested(self, prices_usd: dict, fx: float) -> float:
        return sum(p.shares * prices_usd[t] / fx for t, p in self.positions.items())

    def weights(self, prices_usd: dict, fx: float) -> dict:
        total = self.value(prices_usd, fx)
        return {t: p.shares * prices_usd[t] / fx / total for t, p in self.positions.items()}


def fee(value_eur: float) -> float:
    return max(config.FEE_MIN_EUR, value_eur * config.FEE_RATE)


def execute(depot: Depot, order: Order, open_usd: float, fx: float, day: str):
    """Führt eine Order zum Eröffnungskurs aus. Gibt eine Transaktion (dict) zurück oder None."""
    if order.action == "KAUF":
        price_usd = open_usd * (1 + config.SLIPPAGE)
        price_eur = price_usd / fx
        shares = order.shares
        # Nicht mehr kaufen, als Geld da ist
        while shares > 0 and shares * price_eur + fee(shares * price_eur) > depot.cash:
            shares -= 1
        if shares <= 0:
            return None
        value = shares * price_eur
        f = fee(value)
        depot.cash -= value + f
        pos = depot.positions.get(order.ticker)
        if pos:
            total = pos.shares + shares
            pos.avg_cost_eur = (pos.avg_cost_eur * pos.shares + value) / total
            pos.shares = total
        else:
            depot.positions[order.ticker] = Position(shares, value / shares, open_usd, day)
        return dict(day=day, ticker=order.ticker, action="KAUF", shares=shares, price_usd=price_usd,
                    fx=fx, value_eur=value, fee_eur=f, pnl_eur=0.0, reason=order.reason)

    pos = depot.positions.get(order.ticker)
    if not pos:
        return None
    shares = min(order.shares, pos.shares)
    price_usd = open_usd * (1 - config.SLIPPAGE)
    value = shares * price_usd / fx
    f = fee(value)
    pnl = value - shares * pos.avg_cost_eur - f
    depot.cash += value - f
    pos.shares -= shares
    if pos.shares == 0:
        del depot.positions[order.ticker]
    return dict(day=day, ticker=order.ticker, action="VERKAUF", shares=shares, price_usd=price_usd,
                fx=fx, value_eur=value, fee_eur=f, pnl_eur=pnl, reason=order.reason)
