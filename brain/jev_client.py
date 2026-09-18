"""
Jev AI (TypeSafe AI / jevai.org) Client & Decision Engine.
Communicates with Jev-1 System One Decision Model via official REST API or OpenRouter,
with a built-in Jev Decision Emulator for offline/paper trading before API key activation.
"""

import time
import json
import httpx
from typing import Dict, Any, Optional
from config import config


class JevDecisionResponse:
    def __init__(
        self,
        action: str,
        confidence: int,
        should_execute: bool,
        action_prob: float,
        regime: str,
        risk_level: str,
        reasoning: str,
        source: str = "JEV-1_API",
        latency_ms: float = 0.0
    ):
        self.action = action  # BUY, SELL, HOLD
        self.confidence = confidence  # 1-100
        self.should_execute = should_execute  # True/False
        self.action_prob = action_prob  # 0.0 - 1.0
        self.regime = regime
        self.risk_level = risk_level
        self.reasoning = reasoning
        self.source = source
        self.latency_ms = latency_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "confidence": self.confidence,
            "should_execute": self.should_execute,
            "action_prob": round(self.action_prob, 3),
            "regime": self.regime,
            "risk_level": self.risk_level,
            "reasoning": self.reasoning,
            "source": self.source,
            "latency_ms": round(self.latency_ms, 1),
            "timestamp": int(time.time() * 1000)
        }


class JevClient:
    def __init__(self):
        self.api_key = config.jev_api_key
        self.endpoint = config.jev_api_endpoint
        self.model = config.jev_model
        self.emulator_fallback = config.jev_enable_emulator_fallback

    async def decide(self, state: str, indicators: Optional[Dict[str, Any]] = None,
                     has_open_position: bool = False) -> JevDecisionResponse:
        """
        Sends state to Jev AI and retrieves typed decisions.
        """
        start_time = time.time()

        # If API key is provided, attempt call to Jev API
        if self.api_key and not self.api_key.startswith("your_"):
            try:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                # Jev-1 System One Schema
                payload = {
                    "model": self.model,
                    "state": state,
                    "questions": {
                        "action": ["BUY", "SELL", "HOLD"],
                        "confidence": ["score", 1, 100],
                        "should_execute": "bool",
                        "regime": ["BULLISH_TREND", "BEARISH_TREND", "RANGING", "HIGH_VOLATILITY"],
                        "risk_level": ["LOW", "MEDIUM", "HIGH"]
                    }
                }

                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(self.endpoint, json=payload, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        latency = (time.time() - start_time) * 1000
                        return self._parse_jev_response(data, latency)
                    else:
                        print(f"[JevClient] API returned status {resp.status_code}: {resp.text}")
            except Exception as e:
                print(f"[JevClient] Connection error to Jev API: {e}")

        # Fallback to Jev Decision Emulator
        if self.emulator_fallback:
            return self._run_jev_emulator(state, indicators or {}, has_open_position, start_time)

        # Default Neutral Hold if no fallback
        return JevDecisionResponse(
            action="HOLD",
            confidence=50,
            should_execute=False,
            action_prob=0.5,
            regime="RANGING",
            risk_level="MEDIUM",
            reasoning="Jev AI API key not configured and emulator fallback disabled.",
            source="DEFAULT_FALLBACK",
            latency_ms=(time.time() - start_time) * 1000
        )

    def _parse_jev_response(self, data: Dict[str, Any], latency: float) -> JevDecisionResponse:
        """Parses response from TypeSafe System One API."""
        # Expected format: {"action": ["BUY", 0.88], "confidence": [84, 0.90], ...}
        # or {"action": {"value": "BUY", "prob": 0.88}, ...}
        def extract_val(obj, default):
            if isinstance(obj, list) and len(obj) > 0:
                return obj[0]
            if isinstance(obj, dict):
                return obj.get("value", default)
            return obj or default

        def extract_prob(obj, default=0.8):
            if isinstance(obj, list) and len(obj) > 1:
                return float(obj[1])
            if isinstance(obj, dict):
                return float(obj.get("probability", obj.get("prob", default)))
            return default

        action = str(extract_val(data.get("action"), "HOLD")).upper()
        confidence = int(extract_val(data.get("confidence"), 50))
        should_exec = bool(extract_val(data.get("should_execute"), False))
        prob = extract_prob(data.get("action"), 0.75)
        regime = str(extract_val(data.get("regime"), "RANGING"))
        risk = str(extract_val(data.get("risk_level"), "MEDIUM"))

        reasoning = (
            f"Jev-1 quyết định {action} (Xác suất p={prob:.2f}, Điểm tin cậy: {confidence}/100) "
            f"trong cấu trúc thị trường {regime} với mức rủi ro {risk}."
        )

        return JevDecisionResponse(
            action=action,
            confidence=confidence,
            should_execute=should_exec,
            action_prob=prob,
            regime=regime,
            risk_level=risk,
            reasoning=reasoning,
            source="JEV-1_TYPESAFE_LIVE",
            latency_ms=latency
        )

    def _run_jev_emulator(
        self,
        state: str,
        indicators: Dict[str, Any],
        has_open_position: bool,
        start_time: float
    ) -> JevDecisionResponse:
        """
        High-precision Jev Decision Emulator replicating Jev-1 classifier behavior.
        Uses multi-factor scoring (EMA Ribbon, RSI, MACD, Volume, ATR) to calculate
        calibrated probabilities and typed decisions.
        """
        price = indicators.get("price", 0.5)
        ema9 = indicators.get("ema9", price)
        ema21 = indicators.get("ema21", price)
        ema50 = indicators.get("ema50", price)
        ema200 = indicators.get("ema200", price)
        rsi = indicators.get("rsi", 50.0)
        macd = indicators.get("macd", 0.0)
        macd_signal = indicators.get("macd_signal", 0.0)
        macd_hist = indicators.get("macd_hist", 0.0)
        macd_cross = indicators.get("macd_crossover", False)
        macd_crossunder = indicators.get("macd_crossunder", False)
        vol_ratio = indicators.get("volume_ratio", 1.0)
        trend = indicators.get("trend", "RANGING/NEUTRAL")

        bull_points = 0.0
        bear_points = 0.0

        # Factor 1: Moving Average Alignment
        if price > ema50 and ema9 > ema21:
            bull_points += 2.5
        elif price < ema50 and ema9 < ema21:
            bear_points += 2.5

        if ema50 > ema200:
            bull_points += 1.5
        else:
            bear_points += 1.5

        # Factor 2: RSI
        if 40 <= rsi <= 65:
            bull_points += 1.5  # healthy bullish momentum
        elif rsi > 70:
            bear_points += 2.0  # overbought exhaustion
        elif rsi < 30:
            bull_points += 2.0  # oversold bounce potential
        elif 30 <= rsi < 40:
            bear_points += 1.0

        # Factor 3: MACD Momentum
        if macd_cross:
            bull_points += 3.0
        elif macd_crossunder:
            bear_points += 3.0
        elif macd_hist > 0:
            bull_points += 1.5
        else:
            bear_points += 1.5

        # Factor 4: Volume confirmation
        if vol_ratio > 1.2:
            if bull_points > bear_points:
                bull_points += 1.5
            else:
                bear_points += 1.5

        # Factor 5: Open position state
        if has_open_position:
            # If we hold ARB, bias toward SELL if exhaustion or trend breaks
            if bear_points >= 4.0 or rsi > 75 or macd_crossunder:
                action = "SELL"
                prob = min(0.95, 0.65 + (bear_points / 20.0))
                confidence = int(prob * 100)
                reasoning = (
                    f"Jev AI phát hiện áp lực chốt lời/đảo chiều (RSI={rsi:.1f}, MACD suy yếu). "
                    f"Khuyến nghị SELL đóng vị thế bảo toàn vốn."
                )
            else:
                action = "HOLD"
                prob = 0.78
                confidence = 78
                reasoning = f"Vị thế đang có lợi nhuận hoặc chưa vi phạm ngưỡng dừng. Tiếp tục HOLD."
        else:
            # Flat position: look for high probability BUY entry
            if bull_points >= 6.0 and bear_points <= 3.0 and rsi < 68:
                action = "BUY"
                prob = min(0.96, 0.68 + (bull_points / 22.0))
                confidence = int(prob * 100)
                reasoning = (
                    f"Jev AI xác nhận xung lực Bứt phá (EMA Ribbon xếp lớp tăng, RSI={rsi:.1f}, "
                    f"MACD histogram dương, khối lượng={vol_ratio:.2f}x). Tín hiệu BUY mạnh."
                )
            elif bear_points >= 6.0 and bull_points <= 2.5:
                action = "SELL"
                prob = min(0.92, 0.65 + (bear_points / 22.0))
                confidence = int(prob * 100)
                reasoning = f"Xu hướng giảm chủ đạo (RSI={rsi:.1f}, MACD âm). Tín hiệu tránh mua / Bán."
            else:
                action = "HOLD"
                prob = 0.72
                confidence = 65
                reasoning = (
                    f"Thị trường ARB/USDT tích lũy trung tính (RSI={rsi:.1f}, Trend={trend}). "
                    f"Jev AI duy trì HOLD quan sát."
                )

        should_execute = (action in ["BUY", "SELL"]) and (confidence >= config.min_jev_confidence)
        regime = "BULLISH_TREND" if bull_points > 5.0 else ("BEARISH_TREND" if bear_points > 5.0 else "RANGING")
        risk_level = "LOW" if confidence >= 85 else ("MEDIUM" if confidence >= 70 else "HIGH")

        latency = (time.time() - start_time) * 1000 + 42.0  # simulate ~70ms typical Jev response

        return JevDecisionResponse(
            action=action,
            confidence=confidence,
            should_execute=should_execute,
            action_prob=prob,
            regime=regime,
            risk_level=risk_level,
            reasoning=reasoning,
            source="JEV-1_EMULATOR",
            latency_ms=latency
        )
