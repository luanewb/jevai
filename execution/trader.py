"""
Autonomous Trading Coordinator Engine for ARB/USDT.
Orchestrates Market Ingestion, Jev AI Brain Invocations, Risk Checks,
Order Execution, and Status Broadcasts.
"""

import time
import sys
import asyncio
from typing import Dict, Any, Optional, List

# Ensure UTF-8 output on Windows consoles
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
from config import config
from core.binance_client import BinanceClient
from analytics.indicators import TechnicalIndicators
from brain.state_builder import JevStateBuilder
from brain.jev_client import JevClient, JevDecisionResponse
from brain.reflection import reflector
from brain.memory import memory_store
from risk.risk_manager import RiskManager


class TradingCoordinator:
    def __init__(self):
        self.binance = BinanceClient()
        self.indicators_calc = TechnicalIndicators()
        self.state_builder = JevStateBuilder()
        self.jev = JevClient()
        self.risk = RiskManager()

        self.is_running = True
        self.cycle_interval = 8  # check every 8 seconds
        self.latest_data: Dict[str, Any] = {
            "status": "INITIALIZING",
            "ticker": {},
            "indicators": {},
            "order_book": {},
            "balance": {},
            "open_position": None,
            "latest_decision": None,
            "trades": [],
            "logs": []
        }
        self._loop_task: Optional[asyncio.Task] = None

    def log(self, message: str):
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        self.latest_data["logs"].insert(0, log_entry)
        if len(self.latest_data["logs"]) > 50:
            self.latest_data["logs"].pop()

    async def start(self):
        """Starts the autonomous trading loop."""
        self.is_running = True
        self.log("Khởi động hệ thống Bot giao dịch ARB/USDT với bộ não Jev AI.")
        self._loop_task = asyncio.create_task(self._run_loop())

    async def stop(self):
        """Pauses the trading loop."""
        self.is_running = False
        self.log("Đã tạm dừng chu kỳ giao dịch tự động.")

    async def emergency_close_all(self) -> Dict[str, Any]:
        """Emergency liquidate all open positions."""
        self.log("⚠️ KÍCH HOẠT LỆNH ĐÓNG KHẨN CẤP TẤT CẢ VỊ THẾ!")
        res = self.binance.close_all_positions()
        self.log(f"Kết quả đóng khẩn cấp: {res}")
        return res

    async def _run_loop(self):
        while True:
            if not self.is_running:
                await asyncio.sleep(2)
                continue

            try:
                # 1. Fetch Ticker & Order Book
                ticker = self.binance.get_ticker()
                current_price = ticker.get("price", 0.0)
                if current_price <= 0:
                    await asyncio.sleep(self.cycle_interval)
                    continue

                order_book = self.binance.get_order_book()
                
                # 2. Fetch OHLCV & Compute Indicators
                df_candles = self.binance.get_ohlcv(timeframe="5m", limit=100)
                indicators = self.indicators_calc.calculate_all(df_candles) if not df_candles.empty else {}

                # 3. Account Balance & Open Position
                balance = self.binance.get_balance(current_price)
                open_pos = self.binance.paper_open_position if self.binance.is_paper else None

                # 4. Check Circuit Breaker
                is_halted, cb_reason = self.risk.check_circuit_breaker(balance.get("total_equity", 1000.0))
                if is_halted:
                    self.log(f"⚠️ {cb_reason}")

                # 5. Position Management (Trailing Stop & Exit evaluation)
                if open_pos:
                    new_sl, sl_raised = self.risk.update_trailing_stop(open_pos, current_price)
                    if sl_raised:
                        self.log(f"📈 Dời Trailing Stop Loss lên: {new_sl:.4f} USDT để bảo vệ lợi nhuận.")

                # 6. Query Jev AI Brain
                state_str = self.state_builder.build_state(
                    ticker=ticker,
                    indicators=indicators,
                    order_book=order_book,
                    balance=balance,
                    open_position=open_pos
                )
                
                decision = await self.jev.decide(
                    state=state_str,
                    indicators=indicators,
                    has_open_position=bool(open_pos)
                )

                # 7. Check Exits for Open Position
                if open_pos and not is_halted:
                    should_exit, exit_reason = self.risk.check_exit(open_pos, current_price, decision)
                    if should_exit:
                        self.log(f"🔔 Thực thi thoát vị thế: {exit_reason}")
                        res = self.binance.execute_paper_order(
                            side="SELL",
                            amount_usdt=0,
                            price=current_price,
                            stop_loss=0,
                            take_profit=0,
                            reason=exit_reason
                        )
                        self.log(f"Đã đóng vị thế: {res.get('status')}")

                        # Trigger Post-Mortem Reflection & Memory Learning (2-Strike Filter)
                        if res.get("status") == "SUCCESS" and "order" in res:
                            order_info = res["order"]
                            refl = await reflector.reflect_on_trade(
                                position=open_pos,
                                exit_price=current_price,
                                pnl=order_info.get("pnl", 0.0),
                                pnl_pct=order_info.get("pnl_pct", 0.0),
                                exit_reason=exit_reason,
                                current_indicators=indicators
                            )
                            if refl.get("promoted"):
                                self.log(f"🧠 [BÀI HỌC ĐƯỢC XÁC NHẬN (2 LẦN) - ĐÃ LƯU BỘ NHỚ] {refl.get('lesson')}")
                            elif not refl.get("is_win", True):
                                self.log(f"🔍 [THEO DÕI LỖI LẦN 1] '{refl.get('category')}': Chưa lưu bộ nhớ, chờ xác nhận nếu tái diễn.")
                            else:
                                self.log(f"✨ [LỆNH THẮNG] {refl.get('lesson')}")

                # 8. Check Entry when Flat
                elif not open_pos and not is_halted:
                    eval_result = self.risk.evaluate_entry(decision, current_price, indicators.get("atr", 0.0), balance)
                    if eval_result.get("approved"):
                        allocated = eval_result["allocated_usdt"]
                        sl = eval_result["stop_loss"]
                        tp = eval_result["take_profit"]
                        reason = f"Jev AI BUY (Conf: {decision.confidence}%, {decision.reasoning})"
                        
                        self.log(f"🚀 Jev AI kích hoạt lệnh BUY: ${allocated} USDT @ {current_price:.4f} (SL: {sl}, TP: {tp})")
                        res = self.binance.execute_paper_order(
                            side="BUY",
                            amount_usdt=allocated,
                            price=current_price,
                            stop_loss=sl,
                            take_profit=tp,
                            reason=reason
                        )
                        self.log(f"Kết quả mở lệnh: {res.get('status')}")

                # 9. Update state snapshot for Dashboard
                eff_risk, eff_conf, adaptive_mode = self.risk.get_adaptive_parameters()
                self.latest_data = {
                    "status": "ACTIVE" if self.is_running else "PAUSED",
                    "ticker": ticker,
                    "indicators": indicators,
                    "order_book": order_book,
                    "balance": balance,
                    "open_position": self.binance.paper_open_position if self.binance.is_paper else None,
                    "latest_decision": decision.to_dict(),
                    "trades": self.binance.paper_trades[-15:],
                    "logs": self.latest_data["logs"],
                    "memory": memory_store.get_summary(),
                    "adaptive_risk": {
                        "status": adaptive_mode,
                        "effective_risk_pct": eff_risk,
                        "effective_min_confidence": eff_conf
                    }
                }

            except Exception as e:
                self.log(f"❌ Lỗi chu kỳ giao dịch: {e}")

            await asyncio.sleep(self.cycle_interval)

coordinator = TradingCoordinator()
