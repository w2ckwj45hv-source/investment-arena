"""
Datenschicht: holt echte Marktdaten von Yahoo Finance und speichert sie zwischen.

- Kurse (Eröffnung, Schluss, Hoch, Tief, Volumen)
- Unternehmenskennzahlen (KGV, Wachstum, Schulden …)
- aktuelle Schlagzeilen
"""
import json
import time
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")
import yfinance as yf  # noqa: E402

import config  # noqa: E402

CACHE = Path(__file__).resolve().parent.parent / "data" / "cache"
CACHE.mkdir(parents=True, exist_ok=True)
yf.set_tz_cache_location(str(CACHE / "yf_tz"))

FIELDS = ["Open", "High", "Low", "Close", "Volume"]


def _fresh(path: Path, max_age_hours: float) -> bool:
    return path.exists() and (time.time() - path.stat().st_mtime) < max_age_hours * 3600


def _history(ticker: str, years: int, refresh: bool) -> pd.DataFrame:
    path = CACHE / f"prices_{ticker.replace('^', '_').replace('=', '_')}.csv"
    if not refresh and _fresh(path, 6):
        return pd.read_csv(path, index_col=0, parse_dates=True)
    df = pd.DataFrame()
    for attempt in range(4):  # Yahoo antwortet manchmal nicht sofort – mehrmals versuchen
        try:
            df = yf.Ticker(ticker).history(period=f"{years}y", auto_adjust=True)
        except Exception:
            df = pd.DataFrame()
        if not df.empty:
            break
        time.sleep(5 * (attempt + 1))
    if df.empty:
        if path.exists():  # offline? dann alte Daten nehmen
            return pd.read_csv(path, index_col=0, parse_dates=True)
        raise RuntimeError(f"Keine Kursdaten für {ticker} erhalten.")
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    df = df[FIELDS]
    df.to_csv(path)
    return df


def load_prices(years: int = 3, refresh: bool = False) -> dict:
    """Liefert {'Open': DataFrame, 'Close': …} mit Datum als Zeilen und Tickern als Spalten.
    Alle Kurse sind in US-Dollar; 'FX' enthält den EUR/USD-Kurs je Tag."""
    tickers = list(config.UNIVERSE) + [config.BENCHMARK]
    raw = {t: _history(t, years, refresh) for t in tickers}
    days = raw[config.BENCHMARK].index  # US-Handelstage
    panel = {f: pd.DataFrame({t: raw[t][f].reindex(days) for t in tickers}).ffill() for f in FIELDS}
    fx = _history(config.FX_TICKER, years, refresh)["Close"]
    panel["FX"] = fx.reindex(days.union(fx.index)).ffill().reindex(days).bfill()
    return panel


def load_fundamentals(refresh: bool = False) -> dict:
    """Aktuelle Unternehmenskennzahlen pro Aktie (einmal täglich aktualisiert)."""
    path = CACHE / "fundamentals.json"
    if not refresh and _fresh(path, 24):
        return json.loads(path.read_text(encoding="utf-8"))
    keys = ["trailingPE", "forwardPE", "pegRatio", "trailingPegRatio", "priceToBook",
            "debtToEquity", "revenueGrowth", "earningsGrowth", "profitMargins",
            "returnOnEquity", "freeCashflow", "marketCap", "sector"]
    out = {}
    for t in config.UNIVERSE:
        try:
            info = yf.Ticker(t).info
            out[t] = {k: info.get(k) for k in keys}
        except Exception:
            out[t] = {}
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


def load_news(refresh: bool = False) -> dict:
    """Aktuelle Schlagzeilen pro Aktie: [{title, publisher, time}]."""
    path = CACHE / "news.json"
    if not refresh and _fresh(path, 3):
        return json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for t in config.UNIVERSE:
        try:
            items = yf.Search(t, news_count=10).news or []
        except Exception:
            items = []
        out[t] = [{"title": n.get("title", ""), "publisher": n.get("publisher", ""),
                   "time": n.get("providerPublishTime"),
                   "related": n.get("relatedTickers") or []}
                  for n in items if n.get("title")]
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


def live_quotes() -> dict:
    """Aktuelle Kurse (Minutentakt) für alle Aktien, den S&P 500 und EUR/USD.
    Gibt {'prices': {ticker: Kurs}, 'fx': EUR/USD, 'time': Zeitstempel} zurück."""
    tickers = list(config.UNIVERSE) + [config.BENCHMARK, config.FX_TICKER]
    df = yf.download(tickers, period="2d", interval="1m", progress=False, threads=False, auto_adjust=True)
    close = df["Close"].ffill()
    last = close.iloc[-1]
    return {"prices": {t: float(last[t]) for t in list(config.UNIVERSE) + [config.BENCHMARK]},
            "fx": float(last[config.FX_TICKER]), "time": close.index[-1]}
