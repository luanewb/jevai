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

    def test_two_strike_mistake_filter(self):
        # 1. First loss of BULL_TRAP (Strike 1) -> Monitored, NOT promoted
        res1 = self.mem.record_trade_reflection(
            trade_id="TEST-1",
            side="BUY",
            entry_price=0.25,
            exit_price=0.24,
            pnl=-5.0,
            pnl_pct=-2.0,
            lesson="Cắt lỗ do dính bẫy giá Bull Trap",
            mistake_category="BULL_TRAP"
        )
        self.assertFalse(res1["promoted"])
        self.assertEqual(res1.get("strike"), 1)
        self.assertEqual(len(self.mem.memory["lessons"]), 0)
        self.assertEqual(self.mem.memory["pending_mistakes"]["BULL_TRAP"]["count"], 1)

        # 2. First loss of another category (OVERBOUGHT) (Strike 1) -> Monitored, NOT promoted
        res2 = self.mem.record_trade_reflection(
            trade_id="TEST-2",
            side="BUY",
            entry_price=0.24,
            exit_price=0.23,
            pnl=-4.0,
            pnl_pct=-1.5,
            lesson="Mua khi RSI quá mua dẫn tới thoái lui",
            mistake_category="OVERBOUGHT"
        )
        self.assertFalse(res2["promoted"])
        self.assertEqual(len(self.mem.memory["lessons"]), 0)
        self.assertEqual(self.mem.memory["pending_mistakes"]["OVERBOUGHT"]["count"], 1)

        # 3. Second loss of BULL_TRAP (Strike 2) -> PROMOTED to official memory!
        res3 = self.mem.record_trade_reflection(
            trade_id="TEST-3",
            side="BUY",
            entry_price=0.23,
            exit_price=0.22,
            pnl=-6.0,
            pnl_pct=-2.5,
            lesson="Cắt lỗ do dính bẫy giá Bull Trap lần 2",
            mistake_category="BULL_TRAP"
        )
        self.assertTrue(res3["promoted"])
        self.assertEqual(res3.get("strikes"), 2)
        self.assertEqual(len(self.mem.memory["lessons"]), 1)
        self.assertIn("XÁC NHẬN LỖI LẶP LẠI (2 LẦN)", self.mem.memory["lessons"][0]["lesson"])
        self.assertEqual(self.mem.memory["pending_mistakes"]["BULL_TRAP"]["count"], 0)

        # 4. Check prompt has confirmed lesson and warning
        prompt = self.mem.get_recent_lessons_prompt()
        self.assertIn("[THUA -2.50%]", prompt)
        self.assertIn("⚠️ CẢNH BÁO", prompt)

        # 5. Winning trade -> resets streak
        res4 = self.mem.record_trade_reflection(
            trade_id="TEST-4",
            side="BUY",
            entry_price=0.22,
            exit_price=0.24,
            pnl=10.0,
            pnl_pct=+4.0,
            lesson="Chốt lời thành công theo ATR",
            mistake_category="TAKE_PROFIT_SUCCESS"
        )
        self.assertTrue(res4["is_win"])
        self.assertEqual(self.mem.memory["stats"]["consecutive_losses"], 0)
        self.assertEqual(self.mem.memory["stats"]["wins"], 1)

        # 6. Test clear_memory()
        self.mem.clear_memory()
        self.assertEqual(len(self.mem.memory["lessons"]), 0)
        self.assertEqual(len(self.mem.memory["pending_mistakes"]), 0)
        self.assertEqual(self.mem.memory["stats"]["total_closed_trades"], 0)

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
        from brain.memory import memory_store
        orig_losses = memory_store.memory.get("stats", {}).get("consecutive_losses", 0)
        try:
            risk = RiskManager()
            # Test normal
            memory_store.memory["stats"]["consecutive_losses"] = 0
            eff_risk, eff_conf, mode = risk.get_adaptive_parameters()
            self.assertIn("OPTIMAL", mode)

            # Test mid defense (2 losses)
            memory_store.memory["stats"]["consecutive_losses"] = 2
            eff_risk, eff_conf, mode = risk.get_adaptive_parameters()
            self.assertIn("DEFENSIVE_MID", mode)

            # Test max defense (3+ losses)
            memory_store.memory["stats"]["consecutive_losses"] = 3
            eff_risk, eff_conf, mode = risk.get_adaptive_parameters()
            self.assertIn("DEFENSIVE_MAX", mode)
        finally:
            memory_store.memory["stats"]["consecutive_losses"] = orig_losses

    def test_state_builder_includes_memory(self):
        ticker = {"price": 0.21, "percentage_24h": 5.0, "volume_24h": 10000000.0}
        ind = {"trend": "BULLISH", "rsi": 60.0, "atr": 0.005}
        order_book = {"bid_ask_ratio": 1.2, "spread_pct": 0.01}
        balance = {"total_equity": 1000.0, "usdt_free": 1000.0}

        state = JevStateBuilder.build_state(ticker, ind, order_book, balance)
        self.assertIn("[AI EXPERIENCE & LESSONS FROM RECENT TRADES]", state)


if __name__ == "__main__":
    unittest.main()
