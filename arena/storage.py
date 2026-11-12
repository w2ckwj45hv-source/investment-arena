"""
Datenbank (SQLite): das Langzeitgedächtnis des Teams.

Hier wird alles gespeichert: Depots, Positionen, Transaktionen, jede Analyse
jedes Agenten, die Team-Meetings, gelernte Lektionen und das Vertrauen in die Agenten.
"""
import json
import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "arena.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS portfolios (
    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, mode TEXT, created TEXT,
    start_day TEXT, last_day TEXT, cash REAL, initial REAL);
CREATE TABLE IF NOT EXISTS positions (
    portfolio_id INTEGER, ticker TEXT, shares INTEGER, avg_cost_eur REAL,
    peak_close REAL, entry_day TEXT, PRIMARY KEY (portfolio_id, ticker));
CREATE TABLE IF NOT EXISTS pending_orders (
    portfolio_id INTEGER, day TEXT, ticker TEXT, action TEXT, shares INTEGER, reason TEXT);
CREATE TABLE IF NOT EXISTS transactions (
    portfolio_id INTEGER, day TEXT, ticker TEXT, action TEXT, shares INTEGER,
    price_usd REAL, fx REAL, value_eur REAL, fee_eur REAL, pnl_eur REAL, reason TEXT);
CREATE TABLE IF NOT EXISTS equity (
    portfolio_id INTEGER, day TEXT, value REAL, cash REAL, invested REAL,
    spx REAL, equal_weight REAL, PRIMARY KEY (portfolio_id, day));
CREATE TABLE IF NOT EXISTS opinions (
    id INTEGER PRIMARY KEY AUTOINCREMENT, portfolio_id INTEGER, day TEXT, agent TEXT,
    ticker TEXT, signal TEXT, score REAL, confidence INTEGER, reasons TEXT,
    evaluated INTEGER DEFAULT 0, correct INTEGER, excess REAL);
CREATE INDEX IF NOT EXISTS idx_op ON opinions (portfolio_id, evaluated, day);
CREATE TABLE IF NOT EXISTS meetings (
    portfolio_id INTEGER, day TEXT, regime TEXT, summary TEXT, details TEXT,
    PRIMARY KEY (portfolio_id, day));
CREATE TABLE IF NOT EXISTS lessons (
    portfolio_id INTEGER, day TEXT, agent TEXT, text TEXT);
CREATE TABLE IF NOT EXISTS trust (
    portfolio_id INTEGER, day TEXT, agent TEXT, value REAL, hit_rate REAL, n INTEGER);
CREATE TABLE IF NOT EXISTS reviews (portfolio_id INTEGER, day TEXT);
CREATE TABLE IF NOT EXISTS broker_orders (
    portfolio_id INTEGER, order_id TEXT PRIMARY KEY, day TEXT, ticker TEXT, action TEXT,
    shares INTEGER, reason TEXT, status TEXT);
"""


class Store:
    def __init__(self, path: Path = DB_PATH):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(str(path), check_same_thread=False)
        self.con.executescript(SCHEMA)

    def q(self, sql: str, params=()) -> pd.DataFrame:
        return pd.read_sql_query(sql, self.con, params=params)

    def exec(self, sql: str, params=()):
        cur = self.con.execute(sql, params)
        self.con.commit()
        return cur

    def many(self, sql: str, rows):
        self.con.executemany(sql, rows)
        self.con.commit()

    # --- Depots ---
    def create_portfolio(self, name, mode, start_day, initial) -> int:
        cur = self.exec(
            "INSERT INTO portfolios (name, mode, created, start_day, last_day, cash, initial) "
            "VALUES (?, ?, datetime('now'), ?, NULL, ?, ?)", (name, mode, start_day, initial, initial))
        return cur.lastrowid

    def portfolios(self) -> pd.DataFrame:
        return self.q("SELECT * FROM portfolios ORDER BY id DESC")

    def portfolio(self, pid) -> dict:
        df = self.q("SELECT * FROM portfolios WHERE id = ?", (pid,))
        return df.iloc[0].to_dict()

    def delete_portfolio(self, pid):
        for t in ["positions", "pending_orders", "transactions", "equity", "opinions",
                  "meetings", "lessons", "trust", "reviews", "broker_orders"]:
            self.con.execute(f"DELETE FROM {t} WHERE portfolio_id = ?", (pid,))
        self.con.execute("DELETE FROM portfolios WHERE id = ?", (pid,))
        self.con.commit()

    def save_meeting(self, pid, day, regime, summary, details: dict):
        self.exec("INSERT OR REPLACE INTO meetings VALUES (?, ?, ?, ?, ?)",
                  (pid, day, regime, summary, json.dumps(details, ensure_ascii=False)))
