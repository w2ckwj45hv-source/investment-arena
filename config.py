"""
AI Investment Arena – zentrale Einstellungen.

Hier kannst du ohne Programmierkenntnisse Dinge ändern, z. B. welche Aktien
das Team beobachtet oder wie vorsichtig der Risk Manager ist.
"""

# Aktien, die das Team beobachtet: Ticker -> (Name, Branche)
UNIVERSE = {
    "AAPL": ("Apple", "Technologie"),
    "MSFT": ("Microsoft", "Technologie"),
    "NVDA": ("Nvidia", "Technologie"),
    "AMZN": ("Amazon", "Handel"),
    "GOOGL": ("Alphabet (Google)", "Kommunikation"),
    "META": ("Meta", "Kommunikation"),
    "TSLA": ("Tesla", "Auto"),
    "JPM": ("JPMorgan Chase", "Finanzen"),
    "JNJ": ("Johnson & Johnson", "Gesundheit"),
    "XOM": ("ExxonMobil", "Energie"),
}

BENCHMARK = "^GSPC"      # S&P 500 als Vergleichsmaßstab
FX_TICKER = "EURUSD=X"   # Wechselkurs: Wie viele US-Dollar kostet 1 Euro?

START_CAPITAL_EUR = 100_000.0

# Kosten beim Handeln (realistisch wie bei einem Online-Broker)
FEE_RATE = 0.001         # 0,1 % Gebühr pro Order
FEE_MIN_EUR = 1.0        # mindestens 1 € pro Order
SLIPPAGE = 0.0005        # 0,05 % schlechterer Ausführungskurs

# Regeln des Risk Managers
RISK = {
    "max_position": 0.15,          # höchstens 15 % des Depots in einer Aktie
    "max_sector": 0.40,            # höchstens 40 % in einer Branche
    "min_cash": 0.05,              # immer mindestens 5 % Bargeld
    "max_invested": {              # wie viel insgesamt investiert sein darf, je nach Marktlage
        "Bullenmarkt": 0.95,
        "Neutral": 0.75,
        "Bärenmarkt": 0.45,
    },
    "vol_budget": 0.035,           # Positionsgröße: 0,035 / Jahresvolatilität (wilde Aktien bekommen weniger)
    "trailing_stop": 0.15,         # Verkauf, wenn eine Aktie 15 % unter ihren Höchststand seit Kauf fällt
    "stop_cooldown_days": 10,      # nach einem Stop-Loss 10 Tage nicht wieder kaufen
}

# Entscheidungsregeln des Portfolio Managers
PM = {
    "buy_threshold": 0.15,     # ab diesem Team-Score wird gekauft
    "sell_threshold": -0.10,   # unter diesem Team-Score wird verkauft
    "min_trade_pct": 0.02,     # Änderungen unter 2 % des Depots werden ignoriert (spart Gebühren)
    # Grundvertrauen in die Analysten – wird durch die Lernfunktion angepasst
    "base_weights": {"market": 1.0, "technical": 1.0, "value": 1.0, "news": 0.7},
}

# Lernfunktion
LEARNING = {
    "review_every_days": 20,   # alle 20 Handelstage gibt es eine Nachbesprechung
    "horizon_days": 20,        # ein Signal wird nach 20 Handelstagen bewertet
    "learning_rate": 0.5,      # wie stark sich das Vertrauen pro Nachbesprechung ändert
    "trust_min": 0.3,
    "trust_max": 2.5,
}

# Zeitraffer-Simulation: wie viele Tage in der Vergangenheit sie beginnt
REPLAY_DAYS = 365
