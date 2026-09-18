"""
Unit and Component Tests for AI Memory and Self-Reflection Features.
"""

import sys
import unittest
import tempfile
import asyncio
from pathlib import Path

# Ensure UTF-8 output
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to sys.path
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from brain.memory import ExperienceMemory
from brain.reflection import TradeReflector
from risk.risk_manager import RiskManager
from brain.state_builder import JevStateBuilder


class TestMemoryAndReflection(unittest.TestCase):
    def setUp(self):
        # Create temp file for isolated testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_file = Path(self.temp_dir.name) / "test_memory.json"
        self.mem = ExperienceMemory(storage_path=self.test_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_memory_storage_and_streak(self):
        # Record a loss
        self.mem.record_trade_reflection(
            trade_id="TEST-1",
            side="BUY",
            entry_price=0.25,
            exit_price=0.24,
            pnl=-5.0,
            pnl_pct=-2.0,
            lesson="Cắt lỗ do dính bẫy giá Bull Trap",
            mistake_category="BULL_TRAP"
        )
        self.assertEqual(self.mem.memory["stats"]["losses"], 1)
        self.assertEqual(self.mem.memory["stats"]["consecutive_losses"], 1)
        self.assertEqual(self.mem.memory["stats"]["wins"], 0)

        # Record a second loss
        self.mem.record_trade_reflection(
            trade_id="TEST-2",
            side="BUY",
            entry_price=0.24,
            exit_price=0.23,
            pnl=-4.0,
            pnl_pct=-1.5,
            lesson="Mua khi RSI quá mua dẫn tới thoái lui",
            mistake_category="OVERBOUGHT"
        )
        self.assertEqual(self.mem.memory["stats"]["consecutive_losses"], 2)

        # Verify prompt format
        prompt = self.mem.get_recent_lessons_prompt()
        self.assertIn("THUA (-)", prompt)
        self.assertIn("CẢNH BÁO", prompt)

        # Record a win -> resets consecutive losses
        self.mem.record_trade_reflection(
            trade_id="TEST-3",
            side="BUY",
            entry_price=0.23,
            exit_price=0.245,
            pnl=8.0,
            pnl_pct=+3.5,
            lesson="Chốt lời thành công theo ATR",
            mistake_category="TAKE_PROFIT_SUCCESS"
        )
        self.assertEqual(self.mem.memory["stats"]["consecutive_losses"], 0)
        self.assertEqual(self.mem.memory["stats"]["wins"], 1)
        self.assertEqual(self.mem.memory["stats"]["consecutive_wins"], 1)

    def test_reflector_heuristic(self):
        reflector = TradeReflector()
        pos = {"id": "TEST-POS", "price": 0.50, "side": "BUY", "reason": "BUY signal"}
        lesson, cat = reflector._generate_heuristic_reflection(
            pos=pos,
            exit_p=0.48,
            pnl=-2.5,
            pnl_pct=-2.1,
            reason="HIT_STOP_LOSS",
            ind={"rsi": 74.0}
        )
        self.assertIsNotNone(lesson)
        self.assertIn("Lỗ", lesson)
        self.assertEqual(cat, "OVERBOUGHT_BULL_TRAP")

    def test_adaptive_risk_shield(self):
        risk = RiskManager()
        # Test normal
        eff_risk, eff_conf, mode = risk.get_adaptive_parameters()
        self.assertIn("OPTIMAL", mode)

    def test_state_builder_includes_memory(self):
        ticker = {"price": 0.21, "percentage_24h": 5.0, "volume_24h": 10000000.0}
        ind = {"trend": "BULLISH", "rsi": 60.0, "atr": 0.005}
        order_book = {"bid_ask_ratio": 1.2, "spread_pct": 0.01}
        balance = {"total_equity": 1000.0, "usdt_free": 1000.0}

        state = JevStateBuilder.build_state(ticker, ind, order_book, balance)
        self.assertIn("[AI EXPERIENCE & LESSONS FROM RECENT TRADES]", state)


if __name__ == "__main__":
    unittest.main()
