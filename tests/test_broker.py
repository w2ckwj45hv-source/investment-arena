"""Prüft den virtuellen Broker. Läuft ohne Internet:  python -m unittest discover tests"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
from arena.broker import Depot, Order, execute, fee  # noqa: E402


class BrokerTest(unittest.TestCase):
    def test_fee_has_a_minimum(self):
        self.assertEqual(fee(100), config.FEE_MIN_EUR)
        self.assertAlmostEqual(fee(50_000), 50_000 * config.FEE_RATE)

    def test_buy_then_sell_accounts_for_every_euro(self):
        depot = Depot(cash=10_000.0)
        buy = execute(depot, Order("AAPL", "KAUF", 10), open_usd=100.0, fx=1.0, day="2026-01-02")
        self.assertEqual(depot.positions["AAPL"].shares, 10)
        self.assertAlmostEqual(depot.cash, 10_000 - buy["value_eur"] - buy["fee_eur"])
        sell = execute(depot, Order("AAPL", "VERKAUF", 10), open_usd=110.0, fx=1.0, day="2026-01-05")
        self.assertNotIn("AAPL", depot.positions)
        self.assertAlmostEqual(sell["pnl_eur"], sell["value_eur"] - buy["value_eur"] - sell["fee_eur"])
        self.assertAlmostEqual(depot.cash, 10_000 - buy["value_eur"] - buy["fee_eur"] + sell["value_eur"] - sell["fee_eur"])

    def test_never_buys_more_than_the_cash_allows(self):
        depot = Depot(cash=250.0)
        tx = execute(depot, Order("AAPL", "KAUF", 10), open_usd=100.0, fx=1.0, day="2026-01-02")
        self.assertEqual(tx["shares"], 2)
        self.assertGreaterEqual(depot.cash, 0)
        self.assertIsNone(execute(Depot(cash=50.0), Order("AAPL", "KAUF", 1), 100.0, 1.0, "2026-01-02"))

    def test_selling_what_you_do_not_own_does_nothing(self):
        self.assertIsNone(execute(Depot(cash=100.0), Order("AAPL", "VERKAUF", 5), 100.0, 1.0, "2026-01-02"))


if __name__ == "__main__":
    unittest.main()
