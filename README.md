# AI Investment Arena

A team of six agents runs a paper-money stock portfolio, holds a meeting after
every US trading day and writes a report you can read on your phone. It runs
for free on GitHub Actions and needs no paid API.

```bash
pip install -r requirements-cloud.txt
python demo.py
```

That replays the last year with real prices and virtual money, without any
account or key, and writes the report to `BERICHT.md`.

> Real prices, virtual money. This is a learning project, not investment
> advice, and nothing here should be used with real money.

## The team

| Agent | Job |
|---|---|
| **Marcus**, market analyst | Is the overall market trending up or down? Which stocks beat it? |
| **Nora**, news analyst | Headlines and unusual news events |
| **Victor**, value investor | Valuation, growth, margins, debt |
| **Tessa**, technical trader | Trends, momentum, breakouts |
| **Rita**, risk manager | Hard limits, trailing stop-loss, veto power |
| **Paul**, portfolio manager | Hears everyone, weights them by track record, decides |

Every 20 trading days the team reviews which analyst's calls beat the market
and shifts its trust accordingly.

## What "AI" means here

The agents are **rule-based**. Each one is a small Python class with explicit,
readable rules, so you can see exactly why a stock was bought. No language
model takes part in any trading decision.

A language model is optional and does one thing: if you set an
`ANTHROPIC_API_KEY`, it writes a plain-language summary of the meeting. Without
a key everything else works the same.

## Honest results

The demo above, run on 12 November 2026 over the previous 252 trading days:

| | Return |
|---|---|
| The team | +11.3 % |
| S&P 500 | +15.2 % |
| Same ten stocks, equal weight | +16.1 % |

The team lost to both benchmarks in that year. Its risk rules kept roughly half
the portfolio in cash at the end. Your numbers will differ, because the demo
always replays the most recent year.

Two limits of the replay you should know:

- **Look-ahead in the fundamentals.** The value investor uses today's company
  figures for every past day, because the free data source has no history of
  them. That flatters the result.
- **No news in the replay.** Past headlines are not available, so the news
  analyst only takes part in live operation.

Treat the replay as a demonstration of how the team behaves, not as a
backtest.

## Three ways to run it

| Mode | What it does | Needs |
|---|---|---|
| **Replay** (`python demo.py`) | Plays the last year day by day with a built-in virtual broker | nothing |
| **Local dashboard** (`streamlit run app.py`) | Web dashboard with charts, the meeting log and every trade | `pip install -r requirements.txt` |
| **Cloud** (GitHub Actions) | Meets after every US market close and sends orders to an Alpaca paper account | free [Alpaca](https://alpaca.markets) paper-trading keys |

For the cloud mode, create your own copy with **Use this template**, then add
the repository secrets `ALPACA_KEY_ID` and `ALPACA_SECRET_KEY`. Until both
exist, the scheduled workflow does nothing. The step-by-step guide is in
[ANLEITUNG.md](ANLEITUNG.md) (German).

The workflow commits the team's memory (a SQLite file) and the daily report
back to your repository, so keep your copy **private** if you do not want your
paper portfolio to be public.

## Change the rules

Everything a non-programmer might want to change is in
[`config.py`](config.py): the stocks, the starting capital, fees, the risk
limits, the buy and sell thresholds and how fast the team learns.

Each agent lives in its own file under [`arena/agents/`](arena/agents/). Adding
an agent means adding one class with an `analyze` method.

## Language

The code is commented in German, and the reports and the dashboard are in
German. Translations are welcome.

## Tests

```bash
python -m unittest discover tests
```

The tests cover the virtual broker and run without internet access.

## License

MIT
