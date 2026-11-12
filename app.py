"""
AI Investment Arena – Live-Dashboard.

Eine Seite, die sich jede Minute selbst aktualisiert:
  1. Laufende Kurse und Börsenstatus
  2. Depotwert in Echtzeit – und ist das Team besser als der Markt?
  3. Was hat das Team entschieden – und warum?
  4. Was denkt jeder Agent?
  5. Entwicklung, Depot-Inhalt, Tagebuch
  6. Details zum Aufklappen

Das Handeln selbst übernimmt der Team-Computer (trader.py) im Hintergrund.
Starten: Doppelklick auf "Start.command"
"""
import html
import json
import math
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

warnings.filterwarnings("ignore")

import config  # noqa: E402
from arena import alpaca, data, explain, llm  # noqa: E402
from arena.agents import AGENT_CLASSES, AGENT_INFO  # noqa: E402
from arena.engine import Simulation, market_open_now, new_portfolio, ny_now  # noqa: E402
from arena.explain import company, eur  # noqa: E402
from arena.storage import Store  # noqa: E402

st.set_page_config(page_title="AI Investment Arena", page_icon="🏛️", layout="wide",
                   initial_sidebar_state="collapsed")
BERLIN = ZoneInfo("Europe/Berlin")
STATUS_FILE = Path(__file__).resolve().parent / "data" / "trader_status.json"

# ---------------------------------------------------------------- Aussehen
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], .stMarkdown, button, input { font-family: 'Inter', sans-serif !important; }
.stApp { background: #F5F6F8; }
.block-container { max-width: 1120px; padding-top: 1.4rem; padding-bottom: 4rem; }
header[data-testid="stHeader"], [data-testid="stSidebar"], [data-testid="collapsedControl"], footer,
#MainMenu, [data-testid="stToolbar"] { display: none !important; }
h1, h2, h3 { letter-spacing: -0.02em; }
.brand { font-size: 1.05rem; font-weight: 700; color: #111827; padding-top: 6px; }
.brand span { color: #6B7280; font-weight: 500; }
.card { background: #fff; border-radius: 18px; padding: 22px 24px; border: 1px solid #ECEEF2;
        box-shadow: 0 1px 2px rgba(16,24,40,.04); }
.hero-label { color: #6B7280; font-size: .95rem; font-weight: 500; }
.hero-value { font-size: 3.1rem; font-weight: 800; color: #111827; line-height: 1.1; margin: 4px 0 6px;
              font-variant-numeric: tabular-nums; }
.up { color: #15803D; } .down { color: #B91C1C; } .muted { color: #6B7280; }
.pill { display: inline-block; padding: 5px 12px; border-radius: 999px; font-size: .82rem; font-weight: 600; }
.pill.green { background: #DCFCE7; color: #166534; } .pill.gray { background: #F3F4F6; color: #374151; }
.pill.red { background: #FEE2E2; color: #991B1B; }
.live-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #16A34A;
            margin-right: 6px; animation: pulse 1.6s infinite; }
@keyframes pulse { 0% { opacity: 1 } 50% { opacity: .25 } 100% { opacity: 1 } }
.verdict { margin-top: 14px; padding: 12px 16px; border-radius: 12px; font-weight: 600; font-size: 1rem; }
.verdict.good { background: #F0FDF4; color: #166534; } .verdict.bad { background: #FEF2F2; color: #991B1B; }
.verdict.info { background: #EFF6FF; color: #1E40AF; }
.section { font-size: 1.25rem; font-weight: 700; color: #111827; margin: 34px 0 12px; }
.section small { font-weight: 500; color: #6B7280; font-size: .9rem; margin-left: 8px; }
.ticker { display: flex; gap: 10px; overflow-x: auto; padding: 2px 0 6px; margin: 14px 0 16px; }
.tick { background: #0F172A; color: #E5E7EB; border-radius: 12px; padding: 10px 14px; min-width: 118px; flex-shrink: 0; }
.tick b { color: #fff; font-size: .9rem; } .tick .px { font-size: 1.05rem; font-weight: 700; color: #fff;
          font-variant-numeric: tabular-nums; }
.tick .ch-up { color: #4ADE80; font-weight: 600; font-size: .85rem; }
.tick .ch-down { color: #F87171; font-weight: 600; font-size: .85rem; }
.order { display: flex; gap: 16px; align-items: flex-start; padding: 16px 0; border-bottom: 1px solid #F1F2F4; }
.order:last-child { border-bottom: none; }
.dot { width: 42px; height: 42px; border-radius: 12px; display: flex; align-items: center; justify-content: center;
       font-size: 1.2rem; flex-shrink: 0; font-weight: 800; }
.dot.buy { background: #DCFCE7; color: #15803D; } .dot.sell { background: #FEE2E2; color: #B91C1C; }
.order-title { font-weight: 700; color: #111827; font-size: 1.02rem; }
.order-sub { color: #4B5563; font-size: .92rem; margin-top: 3px; line-height: 1.45; }
.badge { display: inline-block; font-size: .78rem; font-weight: 600; padding: 2px 9px; border-radius: 99px;
         margin-left: 6px; vertical-align: 2px; }
.badge.wait { background: #FEF3C7; color: #92400E; } .badge.done { background: #DCFCE7; color: #166534; }
.grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
.grid4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
@media (max-width: 900px) { .grid, .grid4 { grid-template-columns: 1fr 1fr; } }
@media (max-width: 600px) { .grid, .grid4 { grid-template-columns: 1fr; } .hero-value { font-size: 2.3rem; } }
.agent { display: flex; flex-direction: column; gap: 10px; height: 100%; }
.agent-head { display: flex; gap: 12px; align-items: center; }
.avatar { width: 46px; height: 46px; border-radius: 50%; background: #F3F4F6; display: flex;
          align-items: center; justify-content: center; font-size: 1.45rem; }
.agent-name { font-weight: 700; color: #111827; } .agent-role { color: #6B7280; font-size: .85rem; }
.agent-text { color: #1F2937; font-size: .95rem; line-height: 1.45; flex-grow: 1; }
.meter { height: 6px; background: #F1F2F4; border-radius: 99px; overflow: hidden; }
.meter > div { height: 100%; background: #2563EB; border-radius: 99px; }
.small { font-size: .82rem; color: #6B7280; }
.pos-name { font-weight: 700; color: #111827; }
.pos-value { font-size: 1.35rem; font-weight: 800; margin: 6px 0 2px; font-variant-numeric: tabular-nums; }
.empty { color: #6B7280; text-align: center; padding: 18px; }
.feed { display: flex; gap: 14px; padding: 10px 0; border-bottom: 1px solid #F1F2F4; }
.feed:last-child { border-bottom: none; }
.feed .when { width: 92px; flex-shrink: 0; color: #6B7280; font-size: .85rem; padding-top: 2px; }
.feed .what { color: #1F2937; font-size: .95rem; }
div[data-testid="stExpander"] { background: #fff; border-radius: 14px; border: 1px solid #ECEEF2; }
.stButton > button[kind="primary"] { border-radius: 12px; font-weight: 700; padding: .7rem 1.4rem; font-size: 1.05rem; }
</style>""", unsafe_allow_html=True)


def H(s: str):
    st.markdown(s, unsafe_allow_html=True)


def esc(s) -> str:
    return html.escape(str(s))


WEEKDAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]


def de_day(d) -> str:
    d = pd.Timestamp(d)
    return f"{WEEKDAYS[d.weekday()]}, {d:%d.%m.}"


# ---------------------------------------------------------------- Daten
@st.cache_resource
def get_store():
    return Store()


@st.cache_data(ttl=55, show_spinner=False)
def live():
    """Live-Kurse (Minutentakt) plus Schlusskurs vom Vortag für die Tagesveränderung."""
    try:
        q = data.live_quotes()
    except Exception:
        return None
    p = data.load_prices()
    closes = p["Close"]
    ts = pd.Timestamp(q["time"]).tz_convert("America/New_York")
    prev = closes.iloc[-2] if closes.index[-1].date() == ts.date() else closes.iloc[-1]
    q["prev"] = {t: float(prev[t]) for t in q["prices"]}
    q["time_berlin"] = ts.tz_convert(BERLIN)
    return q


def next_open_berlin() -> datetime:
    n = ny_now()
    d = n.replace(hour=9, minute=30, second=0, microsecond=0)
    if n >= d:
        d += timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d.astimezone(BERLIN)


def next_close_berlin() -> datetime:
    n = ny_now()
    return n.replace(hour=16, minute=0, second=0, microsecond=0).astimezone(BERLIN)


def trader_status():
    try:
        s = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        age = (datetime.now() - datetime.fromisoformat(s["time"])).total_seconds()
        return age < 180, s["text"]
    except Exception:
        return False, "Team-Computer ist nicht gestartet."


store = get_store()
ports = store.q("SELECT * FROM portfolios WHERE mode IN ('live', 'alpaca') ORDER BY id DESC")
if "pid" not in st.session_state or st.session_state.pid not in set(ports.id):
    st.session_state.pid = int(ports.id.iloc[0]) if not ports.empty else None

# ---------------------------------------------------------------- Kopfzeile & Einstellungen
head_l, head_r = st.columns([4, 1.3])
with head_l:
    H('<div class="brand">🏛️ AI Investment Arena <span>· 6 KI-Agenten, ein Team, ein Depot</span></div>')
with head_r:
    with st.popover("⚙️ Einstellungen", use_container_width=True):
        if len(ports) > 1:
            labels = {int(r.id): r.name for r in ports.itertuples()}
            sel = st.selectbox("Depot anzeigen", list(labels), format_func=labels.get,
                               index=list(labels).index(st.session_state.pid))
            if sel != st.session_state.pid:
                st.session_state.pid = sel
                st.rerun()
        if st.session_state.pid is not None:
            st.markdown("**Team-Meeting von Hand anstoßen**")
            st.caption("Normalerweise nicht nötig – der Team-Computer macht das nach jedem Börsenschluss selbst.")
            if st.button("Jetzt prüfen und ggf. Meeting abhalten"):
                with st.spinner("Das Team bespricht sich …"):
                    sim = Simulation(store, st.session_state.pid, refresh=True)
                    n = sim.execute_at_open() + sim.run()
                live.clear()
                st.success("Erledigt." if n else "Für den letzten Handelstag ist schon alles erledigt.")
            st.divider()
        st.markdown("**Optional: echter Broker** (Alpaca, Übungskonto)")
        st.caption(f"Dann gehen die Orders an einen echten Broker statt an den eingebauten. "
                   f"Kostenlos: [{alpaca.SIGNUP_URL}]({alpaca.SIGNUP_URL}) → Paper Trading → API Keys.")
        if alpaca.configured():
            st.success("Alpaca-Schlüssel sind gespeichert.")
        k = st.text_input("API Key ID", key="k_id")
        s = st.text_input("Secret Key", type="password", key="k_sec")
        if st.button("Verbinden", disabled=not (k and s)):
            ok, msg = alpaca.save_and_test(k, s)
            (st.success if ok else st.error)(msg)
        if alpaca.configured() and st.button("Neues Depot über Alpaca starten"):
            try:
                st.session_state.pid = new_portfolio(store, "alpaca")
                Simulation(store, st.session_state.pid).run()
            except alpaca.AlpacaError as e:
                st.error(str(e))
            st.rerun()
        if st.session_state.pid is not None:
            st.divider()
            if st.checkbox("Dieses Depot löschen"):
                if st.button("Endgültig löschen", type="primary"):
                    store.delete_portfolio(st.session_state.pid)
                    del st.session_state["pid"]
                    st.rerun()
        st.caption("Claude-Protokoll: " + ("an" if llm.available() else "aus (optional, Schlüssel in .env)"))

pid = st.session_state.pid

# ---------------------------------------------------------------- Start
if pid is None:
    H('<h1 style="margin-top:30px">Dein KI-Investment-Team</h1>'
      '<p class="muted" style="font-size:1.1rem;max-width:720px">Sechs KI-Agenten arbeiten zusammen wie ein '
      'Trading-Desk an der Wall Street. Ab dem Start kümmern sie sich in Echtzeit um dein Depot: Jeden Abend '
      'nach Börsenschluss besprechen sie sich, und zur Börseneröffnung am nächsten Tag kaufen und verkaufen sie '
      'zu echten Kursen. Das Geld ist virtuell.</p>')
    with st.container(border=True):
        name = st.text_input("Dein Name", value="")
        st.markdown(f"**Startkapital: {eur(config.START_CAPITAL_EUR)}** (virtuell)")
        if st.button(f"🚀 Mit {eur(config.START_CAPITAL_EUR)} starten", type="primary"):
            with st.spinner("Das Team hält sein erstes Meeting …"):
                st.session_state.pid = new_portfolio(store, "live", name=f"{name.strip() or 'Mein'}s Depot")
                Simulation(store, st.session_state.pid).run()
            st.rerun()
    H('<div class="section">Das Team</div>')
    H('<div class="grid">' + "".join(
        f'<div class="card agent"><div class="agent-head"><div class="avatar">{c.emoji}</div><div>'
        f'<div class="agent-name">{c.name}</div><div class="agent-role">{c.role}</div></div></div>'
        f'<div class="agent-text">{esc(c.description)}</div></div>' for c in AGENT_CLASSES) + "</div>")
    st.stop()

p = store.portfolio(pid)
mode = p["mode"]
initial = float(p["initial"])


# ---------------------------------------------------------------- 1 + 2: Live-Bereich (aktualisiert sich jede Minute)
@st.fragment(run_every="60s")
def live_area():
    q = live()
    eq = store.q("SELECT * FROM equity WHERE portfolio_id = ? ORDER BY day", (pid,))
    pos = store.q("SELECT * FROM positions WHERE portfolio_id = ?", (pid,))
    cash = float(store.portfolio(pid)["cash"])
    if q:
        fx, prices = q["fx"], q["prices"]
    else:
        fx, prices = 1.0, {}
    holdings_value = sum(r.shares * prices.get(r.ticker, 0) / fx for r in pos.itertuples()) if q else \
        (float(eq.invested.iloc[-1]) if not eq.empty else 0.0)
    value = cash + holdings_value
    st.session_state["_live_value"] = value

    # Börsenstatus
    is_open = market_open_now()
    running, ttext = trader_status()
    if is_open:
        market = (f'<span class="pill green"><span class="live-dot"></span>Börse New York geöffnet</span> '
                  f'<span class="small">schließt heute um {next_close_berlin():%H:%M} Uhr</span>')
    else:
        no = next_open_berlin()
        market = (f'<span class="pill gray">Börse New York geschlossen</span> '
                  f'<span class="small">öffnet {de_day(no)} um {no:%H:%M} Uhr</span>')
    comp = ('<span class="pill green">● Team-Computer arbeitet</span>' if running else
            '<span class="pill red">Team-Computer aus – bitte über Start.command starten</span>')
    upd = f'<span class="small">Kurse von {q["time_berlin"]:%H:%M} Uhr</span>' if q else ""
    H(f'<div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-top:10px">{market} {comp} {upd}</div>')

    # Laufband mit Live-Kursen
    if q:
        ticks = []
        for t in config.UNIVERSE:
            ch = (prices[t] / q["prev"][t] - 1) * 100
            ticks.append(f'<div class="tick"><b>{esc(company(t).split(" (")[0])}</b>'
                         f'<div class="px">{prices[t]:,.2f} $</div>'
                         f'<div class="{"ch-up" if ch >= 0 else "ch-down"}">{"▲" if ch >= 0 else "▼"} {ch:+.2f} %</div></div>')
        sp = (prices[config.BENCHMARK] / q["prev"][config.BENCHMARK] - 1) * 100
        ticks.insert(0, f'<div class="tick" style="background:#1E3A8A"><b>S&amp;P 500</b>'
                        f'<div class="px">{prices[config.BENCHMARK]:,.0f}</div>'
                        f'<div class="{"ch-up" if sp >= 0 else "ch-down"}">{"▲" if sp >= 0 else "▼"} {sp:+.2f} %</div></div>')
        H('<div class="ticker">' + "".join(ticks) + "</div>")

    # Depotwert
    team_pct = (value / initial - 1) * 100
    days = len(eq)
    if days < 2 and not q:
        text, kind = "Das Team hat gerade angefangen.", "info"
    else:
        idx_pct = _index_pct(eq, q, initial)
        if abs(team_pct) < 0.01 and len(store.q("SELECT 1 FROM transactions WHERE portfolio_id = ?", (pid,))) == 0:
            text, kind = (f"Das Team hat seine ersten Käufe beschlossen. Sie werden zur nächsten "
                          f"Börseneröffnung ausgeführt. Vergleich mit dem Markt (S&P 500) seit Start: {idx_pct:+.1f} %."), "info"
        else:
            text, good = explain.verdict(team_pct, idx_pct)
            kind = "good" if good else "bad"
    left, right = st.columns([2.2, 1])
    with left:
        H(f'<div class="card"><div style="display:flex;justify-content:space-between;align-items:center">'
          f'<div class="hero-label">{esc(p["name"])} · Wert jetzt</div>'
          f'<span class="pill green"><span class="live-dot"></span>Live</span></div>'
          f'<div class="hero-value">{eur(value)}</div>'
          f'<div class="{"up" if value >= initial else "down"}" style="font-weight:700;font-size:1.1rem">'
          f'{eur(value - initial, True)} ({team_pct:+.2f} %) '
          f'<span class="muted" style="font-weight:500">seit Start am {pd.Timestamp(p["start_day"]):%d.%m.%Y}</span></div>'
          f'<div class="verdict {kind}">{esc(text)}</div></div>')
    with right:
        invested = holdings_value / value * 100 if value else 0
        H(f'<div class="card" style="height:100%"><div class="hero-label">In Aktien angelegt</div>'
          f'<div style="font-size:1.8rem;font-weight:800;margin:4px 0">{invested:.0f} %</div>'
          f'<div class="meter"><div style="width:{min(invested, 100):.0f}%"></div></div>'
          f'<div class="small" style="margin-top:8px">Bargeld: {eur(cash)}</div>'
          f'<div class="small" style="margin-top:14px">Startkapital: {eur(initial)}</div>'
          f'<div class="small" style="margin-top:4px">Handelstage bisher: {max(days - 1, 0)}</div></div>')

    # Depot-Inhalt mit Live-Kursen
    H('<div class="section">Was im Depot liegt<small>live bewertet</small></div>')
    cards = []
    rows = []
    for r in pos.itertuples():
        now = prices.get(r.ticker, 0) / fx if q else r.avg_cost_eur
        v = r.shares * now
        rows.append((v, r, now))
    for v, r, now in sorted(rows, key=lambda x: -x[0]):
        pl = r.shares * (now - r.avg_cost_eur)
        cards.append(f'<div class="card"><div class="pos-name">{esc(company(r.ticker))}</div>'
                     f'<div class="small">{r.shares} Aktien · {v / value * 100:.0f} % vom Depot</div>'
                     f'<div class="pos-value">{eur(v)}</div>'
                     f'<div class="{"up" if pl >= 0 else "down"}" style="font-weight:600">{eur(pl, True)} '
                     f'({(now / r.avg_cost_eur - 1) * 100:+.1f} %)</div></div>')
    cards.append(f'<div class="card"><div class="pos-name">💶 Bargeld</div><div class="small">'
                 f'{cash / value * 100 if value else 100:.0f} % vom Depot</div><div class="pos-value">{eur(cash)}</div>'
                 f'<div class="small">bereit für neue Käufe</div></div>')
    H('<div class="grid4">' + "".join(cards) + "</div>")


def _index_pct(eq, q, initial):
    """Wie viel hat der S&P 500 seit dem Start gemacht (in Euro, live)?"""
    if eq.empty:
        return 0.0
    pnl = data.load_prices()
    start = pd.Timestamp(p["start_day"])
    spx0 = float(pnl["Close"][config.BENCHMARK].loc[start]) / float(pnl["FX"].loc[start])
    if q:
        return ((q["prices"][config.BENCHMARK] / q["fx"]) / spx0 - 1) * 100
    return (float(eq.spx.iloc[-1]) / initial - 1) * 100


live_area()

# ---------------------------------------------------------------- 3. Entscheidungen
meet = store.q("SELECT * FROM meetings WHERE portfolio_id = ? ORDER BY day DESC LIMIT 1", (pid,))
det = json.loads(meet.details[0]) if not meet.empty else None
tx = store.q("SELECT * FROM transactions WHERE portfolio_id = ? ORDER BY rowid DESC", (pid,))
if det:
    mday = pd.Timestamp(meet.day[0])
    pending = store.q("SELECT ticker FROM pending_orders WHERE portfolio_id = ?", (pid,)).ticker.tolist()
    done_tx = {r.ticker: r for r in tx[tx.day > meet.day[0]].itertuples()}
    no = next_open_berlin()
    H(f'<div class="section">Die Entscheidungen des Teams<small>Meeting nach Börsenschluss am {de_day(mday)}</small></div>')
    rows = []
    for o in det.get("orders", []):
        buy = o["action"] == "KAUF"
        if o["ticker"] in done_tx:
            t = done_tx[o["ticker"]]
            badge = f'<span class="badge done">✓ ausgeführt zu {t.price_usd:,.2f} $</span>'
        elif o["ticker"] in pending:
            badge = f'<span class="badge wait">⏳ wird {de_day(no)} um {no:%H:%M} Uhr ausgeführt</span>'
        else:
            badge = ""
        rows.append(
            f'<div class="order"><div class="dot {"buy" if buy else "sell"}">{"+" if buy else "−"}</div><div>'
            f'<div class="order-title">{"Kauft" if buy else "Verkauft"} {esc(company(o["ticker"]))} · '
            f'{o["shares"]} Aktien · ca. {eur(o["value_eur"])}{badge}</div>'
            f'<div class="order-sub">{esc(explain.order_story(o, det))}</div></div></div>')
    H('<div class="card">' + ("".join(rows) if rows else
                              '<div class="empty">Keine Käufe oder Verkäufe – das Team ist mit dem Depot zufrieden.</div>')
      + "</div>")

# ---------------------------------------------------------------- 4. Das Team
if det:
    hits = store.q("SELECT agent, AVG(correct) hit, COUNT(*) n FROM opinions WHERE portfolio_id = ? "
                   "AND evaluated = 1 AND correct IS NOT NULL GROUP BY agent", (pid,)).set_index("agent")
    sells = tx[tx.action == "VERKAUF"]
    stops = tx[tx.reason.str.startswith("Stop-Loss")]
    cards = []
    for c in AGENT_CLASSES:
        if c.key in hits.index and hits.loc[c.key].n >= 10:
            h = hits.loc[c.key]
            foot = (f'<div class="small">Trefferquote {h.hit * 100:.0f} %</div>'
                    f'<div class="meter"><div style="width:{h.hit * 100:.0f}%"></div></div>')
        elif c.key == "pm" and len(sells):
            qv = (sells.pnl_eur > 0).mean() * 100
            foot = (f'<div class="small">{qv:.0f} % der Verkäufe mit Gewinn</div>'
                    f'<div class="meter"><div style="width:{qv:.0f}%"></div></div>')
        elif c.key == "risk":
            foot = f'<div class="small">Notbremse bisher {len(stops)}× gezogen</div>'
        else:
            foot = '<div class="small">Trefferquote wird ab dem 20. Handelstag gemessen</div>'
        cards.append(f'<div class="card agent"><div class="agent-head"><div class="avatar">{c.emoji}</div><div>'
                     f'<div class="agent-name">{c.name}</div><div class="agent-role">{c.role}</div></div></div>'
                     f'<div class="agent-text">{esc(explain.agent_headline(c.key, det))}</div>{foot}</div>')
    H('<div class="section">Was jeder im Team denkt</div><div class="grid">' + "".join(cards) + "</div>")
    if meet.summary[0]:
        H(f'<div class="card" style="margin-top:14px"><b>🤖 Protokoll von Claude:</b> {esc(meet.summary[0])}</div>')

# ---------------------------------------------------------------- 5. Tagebuch
H('<div class="section">Tagebuch des Teams<small>Tag für Tag</small></div>')
events = []
for r in store.q("SELECT day, details FROM meetings WHERE portfolio_id = ? ORDER BY day DESC LIMIT 15", (pid,)).itertuples():
    d = json.loads(r.details)
    n = len(d.get("orders", []))
    regime = d.get("regime", "")
    events.append((r.day, 1, f"🗣️ Team-Meeting ({regime}): "
                   + (f"{n} Order{'s' if n != 1 else ''} beschlossen" if n else "keine Änderungen")))
for r in tx.head(30).itertuples():
    word = "Gekauft" if r.action == "KAUF" else "Verkauft"
    extra = f" · {eur(r.pnl_eur, True)}" if r.action == "VERKAUF" else ""
    events.append((r.day, 0, f"{'🟢' if r.action == 'KAUF' else '🔴'} {word}: {r.shares} × {company(r.ticker)} "
                             f"zu {r.price_usd:,.2f} $ ({eur(r.value_eur)}){extra}"))
for r in store.q("SELECT DISTINCT day FROM lessons WHERE portfolio_id = ?", (pid,)).itertuples():
    events.append((r.day, 2, "🧠 Nachbesprechung: Das Team hat aus seinen Ergebnissen gelernt"))
events.sort(key=lambda e: (e[0], e[1]), reverse=True)
H('<div class="card">' + "".join(
    f'<div class="feed"><div class="when">{de_day(d)}</div><div class="what">{esc(w)}</div></div>'
    for d, _, w in events[:12]) + "</div>")

# ---------------------------------------------------------------- 6. Entwicklung
eq = store.q("SELECT * FROM equity WHERE portfolio_id = ? ORDER BY day", (pid,))
eq["day"] = pd.to_datetime(eq["day"])
H('<div class="section">Entwicklung<small>Team im Vergleich zum Markt, je Börsenschluss</small></div>')
if eq.shape[0] >= 2:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=eq.day, y=eq.spx, name="Markt (S&P 500)", line=dict(color="#9CA3AF", width=2),
                             hovertemplate="%{y:,.0f} €<extra>Markt</extra>"))
    fig.add_trace(go.Scatter(x=eq.day, y=eq.value, name="KI-Team", line=dict(color="#2563EB", width=3.5),
                             hovertemplate="%{y:,.0f} €<extra>Team</extra>"))
    fig.add_hline(y=initial, line=dict(color="#E5E7EB", dash="dot"))
    fig.update_layout(height=330, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor="white", paper_bgcolor="white",
                      legend=dict(orientation="h", y=1.08, x=0), hovermode="x unified",
                      yaxis=dict(gridcolor="#F1F2F4", tickformat=",.0f", ticksuffix=" €"),
                      xaxis=dict(showgrid=False), separators=",.", font=dict(family="Inter"))
    with st.container(border=True):
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
else:
    H('<div class="card empty">Die Kurve wächst ab jetzt mit jedem Börsentag – der erste Punkt kommt nach dem '
      'nächsten Börsenschluss.</div>')

# ---------------------------------------------------------------- 7. Details
H('<div class="section">Für Neugierige</div>')
if det:
    with st.expander("🗣️ Das ganze Team-Meeting nachlesen"):
        days = store.q("SELECT day FROM meetings WHERE portfolio_id = ? ORDER BY day DESC", (pid,)).day.tolist()
        d = st.selectbox("Meeting vom", days, format_func=de_day)
        dd = json.loads(store.q("SELECT details FROM meetings WHERE portfolio_id = ? AND day = ?", (pid, d)).details[0])
        for agent, text in dd["transcript"]:
            a = AGENT_INFO[agent]
            with st.chat_message(a.name, avatar=a.emoji):
                st.markdown(f"**{a.name}** · {a.role}  \n{text}")

    with st.expander("🔎 Begründungen zu einer bestimmten Aktie"):
        pick = st.selectbox("Aktie", list(config.UNIVERSE), format_func=company)
        for key in ["market", "news", "value", "technical", "risk"]:
            o = det["opinions"].get(key, {}).get(pick)
            if o:
                a = AGENT_INFO[key]
                icon = {"KAUFEN": "🟢", "VERKAUFEN": "🔴"}.get(o["signal"], "⚪")
                st.markdown(f"**{a.emoji} {a.name}** – {icon} {o['signal'].capitalize()} "
                            f"(Sicherheit {o['confidence']}/10)")
                for r in o["reasons"]:
                    st.markdown(f"<div class='small' style='margin-left:28px'>• {esc(r)}</div>", unsafe_allow_html=True)

with st.expander("🧠 Was das Team gelernt hat"):
    st.caption("Alle 20 Handelstage prüft das Team seine früheren Einschätzungen. Wer oft richtig lag, "
               "bekommt mehr Gewicht bei Pauls Entscheidungen.")
    les = store.q("SELECT day, agent, text FROM lessons WHERE portfolio_id = ? ORDER BY day DESC", (pid,))
    if les.empty:
        st.write("Noch keine Nachbesprechung. Die erste kommt nach 20 Handelstagen.")
    for d, g in list(les.groupby("day", sort=False))[:6]:
        st.markdown(f"**{de_day(d)}**")
        for r in g.itertuples():
            st.markdown(f"- {AGENT_INFO[r.agent].emoji} {r.text}")

with st.expander("🛡️ Risiko"):
    if eq.shape[0] >= 2:
        dd_team = (eq.value / eq.value.cummax() - 1).min() * 100
        dd_spx = (eq.spx / eq.spx.cummax() - 1).min() * 100
        st.markdown(f"**Größter Rückgang vom Höchststand:** Team {dd_team:.1f} % · Markt {dd_spx:.1f} %")
        r = eq.value.pct_change().dropna()
        if len(r) > 5 and r.std() > 0:
            st.markdown(f"**Schwankung pro Jahr:** Team {r.std() * math.sqrt(252) * 100:.0f} % · Markt "
                        f"{eq.spx.pct_change().std() * math.sqrt(252) * 100:.0f} %")
    st.markdown(f"**Ritas feste Regeln:** höchstens {config.RISK['max_position'] * 100:.0f} % pro Aktie, "
                f"{config.RISK['max_sector'] * 100:.0f} % pro Branche, Notbremse bei "
                f"{config.RISK['trailing_stop'] * 100:.0f} % Rückgang vom Höchststand.")

with st.expander("📜 Alle Käufe und Verkäufe"):
    if tx.empty:
        st.write("Noch keine ausgeführten Orders.")
    else:
        show = pd.DataFrame({"Datum": pd.to_datetime(tx.day).dt.strftime("%d.%m.%Y"),
                             "Aktion": tx.action.str.capitalize(), "Firma": tx.ticker.map(company),
                             "Stück": tx.shares, "Kurs $": tx.price_usd.round(2), "Wert €": tx.value_eur.round(0),
                             "Gebühr €": tx.fee_eur.round(2),
                             "Gewinn/Verlust €": tx.pnl_eur.where(tx.action == "VERKAUF").round(0)})
        st.dataframe(show, hide_index=True, use_container_width=True)

H('<p class="small" style="text-align:center;margin-top:40px">Echte Kurse, virtuelles Geld. Keine Anlageberatung.</p>')
