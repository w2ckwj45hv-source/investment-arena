"""
Technische Kennzahlen – exakt berechnet mit Code, nicht von einer KI geschätzt.

Alle Werte nutzen nur Daten bis zum jeweiligen Tag (kein Blick in die Zukunft).
"""
import numpy as np
import pandas as pd


def _rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def compute(panel: dict, ticker: str) -> pd.DataFrame:
    c, h, l, o, v = (panel[f][ticker] for f in ["Close", "High", "Low", "Open", "Volume"])
    df = pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "volume": v})
    df["sma20"] = c.rolling(20).mean()
    df["sma50"] = c.rolling(50).mean()
    df["sma200"] = c.rolling(200).mean()
    df["rsi"] = _rsi(c)
    ema12, ema26 = c.ewm(span=12, adjust=False).mean(), c.ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]
    std20 = c.rolling(20).std()
    df["bb_upper"] = df["sma20"] + 2 * std20
    df["bb_lower"] = df["sma20"] - 2 * std20
    rets = c.pct_change()
    df["ret_1d"] = rets
    df["ret_20d"] = c.pct_change(20)
    df["ret_60d"] = c.pct_change(60)
    df["ret_120d"] = c.pct_change(120)
    df["vol20"] = rets.rolling(20).std() * np.sqrt(252)       # Jahresvolatilität
    df["vol_median"] = df["vol20"].rolling(252, min_periods=60).median()
    df["high20_prev"] = h.rolling(20).max().shift(1)          # Widerstand
    df["low20_prev"] = l.rolling(20).min().shift(1)           # Unterstützung
    df["high252"] = c.rolling(252, min_periods=60).max()
    df["drawdown252"] = c / df["high252"] - 1
    df["vol_ratio"] = v / v.rolling(20).mean().shift(1)       # Volumen im Vergleich zum Durchschnitt
    df["gap"] = o / c.shift(1) - 1
    return df


def compute_all(panel: dict, tickers: list) -> dict:
    return {t: compute(panel, t) for t in tickers}
