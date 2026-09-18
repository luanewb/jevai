"""
Risk Guardian & Capital Management Engine.
Enforces position sizing, dynamic ATR-based Stop Loss & Take Profit,
Trailing Stop logic, and daily drawdown circuit breakers.
"""

from typing import Dict, Any, Optional, Tuple
from config import config
from brain.jev_client import JevDecisionResponse


class RiskManager:
    def __init__(self):
        self.risk_pct = config.risk_per_trade_percent
        self.min_confidence = config.min_jev_confidence
        self.atr_sl_mult = config.atr_sl_multiplier
        self.atr_tp_mult = config.atr_tp_multiplier
        self.max_daily_drawdown = config.max_daily_drawdown_percent
        self.trailing_enabled = config.trailing_stop_enabled
        self.trailing_callback = config.trailing_stop_callback_percent
        
        self.daily_starting_equity = None
        self.circuit_breaker_triggered = False

    def check_circuit_breaker(self, current_equity: float) -> Tuple[bool, str]:
        """Check if daily loss limit was reached."""
        if self.daily_starting_equity is None:
            self.daily_starting_equity = current_equity

        drawdown = (self.daily_starting_equity - current_equity) / self.daily_starting_equity * 100
        if drawdown >= self.max_daily_drawdown:
            self.circuit_breaker_triggered = True
            return True, f"Mức sụt giảm trong ngày đạt {drawdown:.2f}% (vượt ngưỡng {self.max_daily_drawdown}%). Kích hoạt Circuit Breaker dừng bot."

        return False, "OK"

    def evaluate_entry(
        self,
        decision: JevDecisionResponse,
        current_price: float,
        atr: float,
        balance_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluates whether a BUY entry is approved by Risk Guardian and calculates parameters.
        """
        if self.circuit_breaker_triggered:
            return {"approved": False, "reason": "Circuit Breaker is active. Trading halted for risk safety."}

        if decision.action != "BUY":
            return {"approved": False, "reason": f"Decision is {decision.action}, not BUY."}

        if not decision.should_execute:
            return {"approved": False, "reason": "Jev AI should_execute flag is False."}

        if decision.confidence < self.min_confidence:
            return {
                "approved": False,
                "reason": f"Confidence {decision.confidence}% is below required {self.min_confidence}% threshold."
            }

        usdt_free = balance_info.get("usdt_free", 0.0)
        total_equity = balance_info.get("total_equity", 1000.0)

        if usdt_free < 10.0:
            return {"approved": False, "reason": f"Số dư USDT khả dụng quá thấp (${usdt_free:.2f} < $10)."}

        # Calculate Stop Loss & Take Profit based on ATR
        effective_atr = atr if atr > 0 else (current_price * 0.02)
        sl_distance = effective_atr * self.atr_sl_mult
        tp_distance = effective_atr * self.atr_tp_mult

        stop_loss = round(current_price - sl_distance, 4)
        take_profit = round(current_price + tp_distance, 4)
        risk_reward = round(tp_distance / sl_distance, 2) if sl_distance > 0 else 1.5

        # Position Sizing: Risk X% of equity on this trade
        # Risk amount ($) = total_equity * (risk_pct / 100)
        # Position size ($) = Risk amount / (sl_distance / current_price)
        risk_cash = total_equity * (self.risk_pct / 100.0)
        sl_pct = sl_distance / current_price
        
        target_usdt = risk_cash / sl_pct if sl_pct > 0 else (total_equity * 0.1)
        # Cap position size to maximum 30% of total equity for safe diversification
        max_allowed_position = total_equity * 0.30
        target_usdt = min(target_usdt, max_allowed_position, usdt_free * 0.95)

        if target_usdt < 10.0:
            target_usdt = min(15.0, usdt_free * 0.9)

        return {
            "approved": True,
            "allocated_usdt": round(target_usdt, 2),
            "entry_price": current_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_reward_ratio": risk_reward,
            "risk_cash": round(risk_cash, 2),
            "reason": "Risk parameters verified and approved."
        }

    def update_trailing_stop(
        self,
        position: Dict[str, Any],
        current_price: float
    ) -> Tuple[float, bool]:
        """
        Updates trailing stop loss if enabled and price makes a higher high.
        Returns: (new_sl, was_updated)
        """
        current_sl = position.get("stop_loss", 0.0)
        highest_price = position.get("highest_price", position["price"])

        if current_price > highest_price:
            position["highest_price"] = current_price
            if self.trailing_enabled:
                trailing_sl = current_price * (1.0 - (self.trailing_callback / 100.0))
                if trailing_sl > current_sl:
                    position["stop_loss"] = round(trailing_sl, 4)
                    return round(trailing_sl, 4), True

        return current_sl, False

    def check_exit(
        self,
        position: Dict[str, Any],
        current_price: float,
        decision: JevDecisionResponse
    ) -> Tuple[bool, str]:
        """
        Checks if open position should be closed via Stop Loss, Take Profit, or Jev AI SELL signal.
        """
        entry_price = position.get("price", current_price)
        stop_loss = position.get("stop_loss", 0.0)
        take_profit = position.get("take_profit", 999999.0)

        # 1. Stop Loss Hit
        if current_price <= stop_loss:
            return True, f"HIT_STOP_LOSS (Giá {current_price:.4f} chạm mức SL {stop_loss:.4f})"

        # 2. Take Profit Hit
        if current_price >= take_profit:
            return True, f"HIT_TAKE_PROFIT (Giá {current_price:.4f} chạm mục tiêu TP {take_profit:.4f})"

        # 3. Jev AI SELL signal
        if decision.action == "SELL" and decision.confidence >= self.min_confidence:
            return True, f"JEV_AI_SELL_SIGNAL (Độ tin cậy: {decision.confidence}%, {decision.reasoning})"

        return False, "HOLD"
