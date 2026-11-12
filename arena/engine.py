"""
Simulations-Engine: lässt das Team Tag für Tag handeln.

Ablauf eines Handelstages:
  Morgens  – Orders vom Vortag werden zum Eröffnungskurs ausgeführt
  Abends   – Depot wird bewertet, ggf. Nachbesprechung (Lernen),
             dann Team-Meeting: alle Agenten analysieren, der PM entscheidet,
             die Orders werden für den nächsten Morgen vorgemerkt

Betriebsarten, gleicher Team-Code:
  Zeitraffer – startet in der Vergangenheit und spielt jeden Tag bis heute nach
  Live       – startet heute, Orders werden intern simuliert
  Alpaca     – startet heute, Orders gehen wirklich an den Broker Alpaca (Paper-Konto)
"""
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

import config
from arena import alpaca, data, indicators, learning, llm
from arena.agents import AGENT_CLASSES
from arena.brain import DayContext, TeamBrain
from arena.broker import Depot, Order, Position, execute

SECTORS = {t: v[1] for t, v in config.UNIVERSE.items()}


def ny_now():
    return datetime.now(ZoneInfo("America/New_York"))


def market_open_now() -> bool:
    """Ist die Börse in New York gerade geöffnet (Mo–Fr 9:30–16:00 Ortszeit)?"""
    n = ny_now()
    return n.weekday() < 5 and (9, 30) <= (n.hour, n.minute) < (16, 0)


def trading_dates(panel):
    """Entfernt einen noch laufenden Handelstag (Börse New York noch offen)."""
    dates = panel["Close"].index
    ny = ny_now()
    if dates[-1].date() == ny.date() and (ny.hour, ny.minute) < (16, 30):
        dates = dates[:-1]
    return dates


class Simulation:
    def __init__(self, store, pid, refresh=False):
        self.store, self.pid = store, pid
        self.p = store.portfolio(pid)
        self.panel = data.load_prices(refresh=refresh)
        self.fundamentals = data.load_fundamentals(refresh=refresh)
        self.tickers = list(config.UNIVERSE)
        self.frames = indicators.compute_all(self.panel, self.tickers)
        self.bench = indicators.compute(self.panel, config.BENCHMARK)
        self.dates = trading_dates(self.panel)
        self.close, self.open, self.fx = self.panel["Close"], self.panel["Open"], self.panel["FX"]
        self.idx = {d.strftime("%Y-%m-%d"): k for k, d in enumerate(self.dates)}
        self.agents = {c.key: c() for c in AGENT_CLASSES}
        self._load_state()

    # ---------- Zustand laden/speichern ----------
    def _load_state(self):
        pos = self.store.q("SELECT * FROM positions WHERE portfolio_id = ?", (self.pid,))
        self.depot = Depot(cash=float(self.p["cash"]))
        for r in pos.itertuples():
            self.depot.positions[r.ticker] = Position(int(r.shares), r.avg_cost_eur, r.peak_close, r.entry_day)
        tr = self.store.q("SELECT agent, value FROM trust WHERE portfolio_id = ? ORDER BY rowid", (self.pid,))
        trust = {a: 1.0 for a in learning.ANALYSTS}
        trust.update(dict(zip(tr.agent, tr.value)))
        self.brain = TeamBrain(trust=trust)
        self.cooldown = {}
        stops = self.store.q("SELECT day, ticker FROM transactions WHERE portfolio_id = ? AND reason LIKE 'Stop-Loss%'",
                             (self.pid,))
        for r in stops.itertuples():
            if r.day in self.idx:
                self.cooldown[r.ticker] = self.idx[r.day] + config.RISK["stop_cooldown_days"]
        start = self.dates[self.dates >= pd.Timestamp(self.p["start_day"])]
        self.i_start = self.idx[start[0].strftime("%Y-%m-%d")] if len(start) else len(self.dates) - 1

    def _save_state(self, day=None):
        s, pid = self.store, self.pid
        s.con.execute("DELETE FROM positions WHERE portfolio_id = ?", (pid,))
        s.con.executemany("INSERT INTO positions VALUES (?, ?, ?, ?, ?, ?)",
                          [(pid, t, p.shares, p.avg_cost_eur, p.peak_close, p.entry_day)
                           for t, p in self.depot.positions.items()])
        s.con.execute("UPDATE portfolios SET cash = ? WHERE id = ?", (self.depot.cash, pid))
        if day:
            s.con.execute("UPDATE portfolios SET last_day = ? WHERE id = ?", (day, pid))
        s.con.commit()

    def _execute_pending(self, open_prices: dict, fx: float, ds: str, i: int):
        pend = self.store.q("SELECT * FROM pending_orders WHERE portfolio_id = ?", (self.pid,))
        txs = []
        for r in pend.itertuples():  # Verkäufe stehen zuerst in der Liste
            tx = execute(self.depot, Order(r.ticker, r.action, int(r.shares), r.reason),
                         float(open_prices[r.ticker]), fx, ds)
            if tx:
                txs.append(tx)
                if tx["reason"].startswith("Stop-Loss"):
                    self.cooldown[tx["ticker"]] = i + config.RISK["stop_cooldown_days"]
        self.store.exec("DELETE FROM pending_orders WHERE portfolio_id = ?", (self.pid,))
        if txs:
            self.store.many("INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            [(self.pid, t["day"], t["ticker"], t["action"], t["shares"], t["price_usd"],
                              t["fx"], t["value_eur"], t["fee_eur"], t["pnl_eur"], t["reason"]) for t in txs])
        return txs

    def execute_at_open(self) -> int:
        """Echtzeit: Sobald die Börse heute geöffnet hat, werden die Orders aus dem letzten
        Meeting zum echten Eröffnungskurs von heute ausgeführt."""
        if self.p["mode"] != "live" or not market_open_now():
            return 0
        today = pd.Timestamp(ny_now().date())
        if today not in self.panel["Open"].index:
            return 0  # Feiertag oder noch keine Daten
        opens = self.panel["Open"].loc[today]
        fx = float(self.panel["FX"].iloc[-1])
        txs = self._execute_pending(opens.to_dict(), fx, today.strftime("%Y-%m-%d"), len(self.dates))
        self._save_state()
        return len(txs)

    # ---------- Hauptschleife ----------
    def _review_due(self, i) -> bool:
        r = self.store.q("SELECT MAX(day) d FROM reviews WHERE portfolio_id = ?", (self.pid,)).d[0]
        since = self.idx.get(r, self.i_start) if r else self.i_start
        return i - since >= config.LEARNING["review_every_days"]

    def _review(self, i):
        if self._review_due(i):
            learning.review(self.store, self.pid, i, self.dates, self.close, self.close[config.BENCHMARK], self.brain)
            self.store.exec("INSERT INTO reviews VALUES (?, ?)", (self.pid, self.dates[i].strftime("%Y-%m-%d")))

    def _record_equity(self, i, ds, value, cash, fx):
        k0, initial = self.i_start, float(self.p["initial"])
        fx0, bc = float(self.fx.iloc[k0]), self.close[config.BENCHMARK]
        spx = initial * (bc.iloc[i] / fx) / (bc.iloc[k0] / fx0)
        ew = initial * sum(self.close[t].iloc[i] / self.close[t].iloc[k0] for t in self.tickers) / len(self.tickers) * fx0 / fx
        self.store.exec("INSERT OR REPLACE INTO equity VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (self.pid, ds, value, cash, value - cash, float(spx), float(ew)))

    def run(self, progress=None):
        if self.p["mode"] == "alpaca":
            return self.run_alpaca()
        last = self.p["last_day"]
        i0 = self.idx[last] + 1 if last and last in self.idx else self.i_start
        total = len(self.dates) - i0
        for n, i in enumerate(range(i0, len(self.dates))):
            self.step(i)
            if progress:
                progress((n + 1) / max(total, 1), self.dates[i])
        return total

    def step(self, i):
        day = self.dates[i]
        ds = day.strftime("%Y-%m-%d")
        fx = float(self.fx.iloc[i])

        # 1) Morgens: vorgemerkte Orders zum Eröffnungskurs ausführen
        #    (im Echtzeit-Betrieb ist das meist schon zur Börseneröffnung passiert)
        self._execute_pending(self.open.iloc[i].to_dict(), fx, ds, i)

        # 2) Abends: Depot bewerten
        prices = {t: float(self.close[t].iloc[i]) for t in self.tickers}
        for t, p in self.depot.positions.items():
            p.peak_close = max(p.peak_close, prices[t])
        self._record_equity(i, ds, self.depot.value(prices, fx), self.depot.cash, fx)

        # 3) Nachbesprechung (Lernen)
        self._review(i)

        # 4) Team-Meeting
        is_live_today = self.p["mode"] == "live" and i == len(self.dates) - 1
        ctx = DayContext(day=day, i=i, frames=self.frames, bench=self.bench, fundamentals=self.fundamentals,
                         news=data.load_news() if is_live_today else None, depot=self.depot,
                         prices=prices, fx=fx, cooldown=self.cooldown, sectors=SECTORS)
        orders = self.meeting(ctx, ds, use_llm=is_live_today)
        self.store.many("INSERT INTO pending_orders VALUES (?, ?, ?, ?, ?, ?)",
                        [(self.pid, ds, o.ticker, o.action, o.shares, o.reason) for o in orders])
        self._save_state(ds)

    # ---------- Echter Broker (Alpaca Paper) ----------
    def run_alpaca(self):
        """Ein Team-Meeting pro Handelstag; die Orders gehen wirklich an Alpaca."""
        i = len(self.dates) - 1
        ds = self.dates[i].strftime("%Y-%m-%d")
        if self.p["last_day"] == ds:
            return 0
        api = alpaca.client()
        fx = float(self.fx.iloc[i])
        self._sync_fills(api)
        acc = api.account()
        self._sync_depot(api, fx, ds)
        prices = {t: float(self.close[t].iloc[i]) for t in self.tickers}
        self._record_equity(i, ds, float(acc["equity"]) / fx, self.depot.cash, fx)
        self._review(i)

        ctx = DayContext(day=self.dates[i], i=i, frames=self.frames, bench=self.bench,
                         fundamentals=self.fundamentals, news=data.load_news(), depot=self.depot,
                         prices=prices, fx=fx, cooldown=self.cooldown, sectors=SECTORS)
        orders = self.meeting(ctx, ds, use_llm=True)
        api.cancel_open_orders()  # alte, nicht ausgeführte Orders verwerfen
        for o in orders:  # Verkäufe zuerst
            try:
                res = api.submit(o.ticker, o.shares, "buy" if o.action == "KAUF" else "sell")
                self.store.exec("INSERT OR REPLACE INTO broker_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                (self.pid, res["id"], ds, o.ticker, o.action, o.shares, o.reason, res["status"]))
            except alpaca.AlpacaError as e:
                self.store.exec("INSERT OR REPLACE INTO broker_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                (self.pid, f"fehler-{ds}-{o.ticker}", ds, o.ticker, o.action, o.shares,
                                 o.reason, f"abgelehnt: {e}"))
        self._save_state(ds)
        return 1

    def _sync_fills(self, api):
        """Holt ausgeführte Orders von Alpaca und trägt sie als Transaktionen ein."""
        open_ = self.store.q("SELECT * FROM broker_orders WHERE portfolio_id = ? AND status NOT IN "
                             "('filled', 'canceled', 'expired', 'rejected') AND status NOT LIKE 'abgelehnt%'", (self.pid,))
        for r in open_.itertuples():
            o = api.order(r.order_id)
            status = o["status"]
            qty = int(float(o.get("filled_qty") or 0))
            if qty > 0 and status in ("filled", "canceled", "expired"):
                price = float(o["filled_avg_price"])
                day = (o.get("filled_at") or r.day)[:10]
                fx = float(self.fx.asof(pd.Timestamp(day)))
                pos = self.depot.positions.get(r.ticker)
                pnl = (price / fx - pos.avg_cost_eur) * qty if r.action == "VERKAUF" and pos else 0.0
                self.store.exec("INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                (self.pid, day, r.ticker, r.action, qty, price, fx, qty * price / fx, 0.0, pnl, r.reason))
                if r.reason.startswith("Stop-Loss") and day in self.idx:
                    self.cooldown[r.ticker] = self.idx[day] + config.RISK["stop_cooldown_days"]
            self.store.exec("UPDATE broker_orders SET status = ? WHERE order_id = ?", (status, r.order_id))

    def _sync_depot(self, api, fx, ds):
        """Übernimmt Bargeld und Positionen aus dem Alpaca-Konto."""
        acc = api.account()
        old = self.depot.positions
        self.depot = Depot(cash=float(acc["cash"]) / fx)
        for p in api.positions():
            t = p["symbol"]
            if t not in config.UNIVERSE:
                continue
            prev = old.get(t)
            price = float(p["current_price"])
            self.depot.positions[t] = Position(int(float(p["qty"])), float(p["avg_entry_price"]) / fx,
                                               max(prev.peak_close, price) if prev else price,
                                               prev.entry_day if prev else ds)

    def meeting(self, ctx, ds, use_llm=False):
        brain, A = self.brain, self.agents
        brain.new_day()
        # Reihenfolge: Marktlage zuerst (alle brauchen sie), dann die Analysten, dann Risiko
        for key in ["market", "news", "value", "technical", "risk"]:
            A[key].analyze(ctx, brain)
        current = self.depot.weights(ctx.prices, ctx.fx)
        targets = A["pm"].propose(ctx, brain, current)
        final = A["risk"].review(targets, current, ctx, brain)
        orders = A["pm"].make_orders(final, current, ctx, brain)

        # Analysen ins Langzeitgedächtnis schreiben
        self.store.many(
            "INSERT INTO opinions (portfolio_id, day, agent, ticker, signal, score, confidence, reasons) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [(self.pid, ds, o.agent, o.ticker, o.signal, o.score, o.confidence,
              json.dumps(o.reasons, ensure_ascii=False)) for o in brain.all_opinions()])

        summary = None
        if use_llm and llm.available():
            text = "\n\n".join(f"[{A[k].name} – {A[k].role}] {t}" for k, t in brain.transcript)
            summary = llm.summarize_meeting(text)
        details = {
            "regime": brain.market_view.get("regime", ""),
            "limits": {"max_invested": brain.risk_limits["max_invested"], "stops": brain.risk_limits["stops"],
                       "vetoes": brain.risk_limits.get("vetoes", [])},
            "orders": [{"ticker": o.ticker, "action": o.action, "shares": o.shares,
                        "value_eur": round(o.shares * ctx.prices[o.ticker] / ctx.fx), "reason": o.reason}
                       for o in orders],
            "depot_value": ctx.depot.value(ctx.prices, ctx.fx),
            "prices_eur": {t: round(px / ctx.fx, 4) for t, px in ctx.prices.items()},
            "transcript": brain.transcript,
            "team_scores": {t: round(s, 3) for t, (s, _) in A["pm"].scores.items()},
            "targets": {t: round(w, 4) for t, w in final.items()},
            "trust": brain.trust,
            "lessons": brain.lessons,
            "opinions": {a: {t: {"signal": o.signal, "score": o.score, "confidence": o.confidence,
                                 "reasons": o.reasons} for t, o in ops.items()}
                         for a, ops in brain.whiteboard.items()},
        }
        brain.lessons = []
        self.store.save_meeting(self.pid, ds, brain.market_view.get("regime", ""), summary, details)
        return orders


def new_portfolio(store, mode: str, name: str = None):
    """Legt ein neues Depot an. mode = 'replay' (Zeitraffer), 'live' (intern) oder 'alpaca' (Broker)."""
    panel = data.load_prices()
    dates = trading_dates(panel)
    initial = config.START_CAPITAL_EUR
    if mode == "replay":
        start = dates[dates >= dates[-1] - pd.Timedelta(days=config.REPLAY_DAYS)][0]
        name = name or f"Zeitraffer ab {start:%d.%m.%Y}"
    elif mode == "alpaca":
        start = dates[-1]
        acc = alpaca.client().account()
        initial = float(acc["equity"]) / float(panel["FX"].loc[start])
        name = name or f"Alpaca-Depot ab {start:%d.%m.%Y}"
    else:
        start = dates[-1]
        name = name or f"Live-Depot ab {start:%d.%m.%Y}"
    return store.create_portfolio(name, mode, start.strftime("%Y-%m-%d"), initial)
