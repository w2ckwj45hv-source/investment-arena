"""Das Team: 6 Agenten mit je eigenem kleinem Gehirn."""
from arena.agents.market import MarketAnalyst
from arena.agents.news import NewsAnalyst
from arena.agents.portfolio import PortfolioManager
from arena.agents.risk import RiskManager
from arena.agents.technical import TechnicalTrader
from arena.agents.value import ValueInvestor

AGENT_CLASSES = [MarketAnalyst, NewsAnalyst, ValueInvestor, TechnicalTrader, RiskManager, PortfolioManager]
AGENT_INFO = {c.key: c for c in AGENT_CLASSES}
