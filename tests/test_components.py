"""
Unit and Component Tests for Jev AI Binance ARB/USDT Trading Bot.
"""

import unittest
import pandas as pd
import numpy as np
from analytics.indicators import TechnicalIndicators
from brain.state_builder import JevStateBuilder
from brain.jev_client import JevClient
from risk.risk_manager import RiskManager
from version import get_version, bump_version


class TestJevTradingBot(unittest.TestCase):
    def setUp(self):
        # Generate synthetic 5m OHLCV data for ARB/USDT
        np.random.seed(42)
        n = 100
        timestamps = [1700000000000 + i * 300000 for i in range(n)]
        base_price = 0.50
        prices = [base_price]
        for _ in range(1, n):
            change = np.random.normal(0, 0.003)
            prices.append(prices[-1] * (1 + change))

        data = []
        for i in range(n):
            p = prices[i]
            high = p * (1 + np.random.uniform(0.001, 0.005))
            low = p * (1 - np.random.uniform(0.001, 0.005))
            open_p = p * (1 + np.random.uniform(-0.002, 0.002))
            vol = np.random.uniform(10000, 50000)
            data.append([timestamps[i], open_p, high, low, p, vol])

        self.df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume"])

    def test_technical_indicators(self):
        ind = TechnicalIndicators.calculate_all(self.df)
        self.assertIn("rsi", ind)
        self.assertIn("ema9", ind)
        self.assertIn("ema50", ind)
        self.assertIn("atr", ind)
        self.assertIn("macd", ind)
        self.assertGreater(ind["price"], 0)
        self.assertTrue(0 <= ind["rsi"] <= 100)
        self.assertGreater(ind["atr"], 0)

    def test_state_builder(self):
        ind = TechnicalIndicators.calculate_all(self.df)
        ticker = {"price": ind["price"], "percentage_24h": 2.5, "volume_24h": 15000000.0}
        order_book = {"bid_ask_ratio": 1.45, "spread_pct": 0.02}
        balance = {"total_equity": 1000.0, "usdt_free": 950.0}
        
        state = JevStateBuilder.build_state(ticker, ind, order_book, balance)
        self.assertIn("[MARKET: ARB/USDT on Binance]", state)
        self.assertIn("Current Price", state)
        self.assertIn("RSI(14)", state)
        self.assertIn("Available USDT", state)

    async def async_test_jev_emulator(self):
        ind = TechnicalIndicators.calculate_all(self.df)
        ticker = {"price": ind["price"], "percentage_24h": 2.5, "volume_24h": 15000000.0}
        order_book = {"bid_ask_ratio": 1.45, "spread_pct": 0.02}
        balance = {"total_equity": 1000.0, "usdt_free": 950.0}
        state = JevStateBuilder.build_state(ticker, ind, order_book, balance)

        client = JevClient()
        client.emulator_fallback = True
        decision = await client.decide(state, ind, has_open_position=False)

        self.assertIn(decision.action, ["BUY", "SELL", "HOLD"])
        self.assertTrue(0 <= decision.confidence <= 100)
        self.assertTrue(0.0 <= decision.action_prob <= 1.0)
        self.assertIsNotNone(decision.reasoning)

    def test_jev_client_sync(self):
        import asyncio
        asyncio.run(self.async_test_jev_emulator())

    def test_risk_manager_evaluation(self):
        risk = RiskManager()
        from brain.jev_client import JevDecisionResponse
        buy_decision = JevDecisionResponse(
            action="BUY",
            confidence=85,
            should_execute=True,
            action_prob=0.88,
            regime="BULLISH_TREND",
            risk_level="LOW",
            reasoning="Strong bullish momentum"
        )
        balance = {"total_equity": 1000.0, "usdt_free": 1000.0}
        eval_res = risk.evaluate_entry(buy_decision, current_price=0.55, atr=0.01, balance_info=balance)
        self.assertTrue(eval_res["approved"])
        self.assertGreater(eval_res["allocated_usdt"], 0)
        self.assertLess(eval_res["stop_loss"], 0.55)
        self.assertGreater(eval_res["take_profit"], 0.55)


if __name__ == "__main__":
    unittest.main()
