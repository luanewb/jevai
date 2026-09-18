"""
Post-Mortem Trade Reflection Engine for Jev AI.
Analyzes concluded trades to extract actionable lessons and save to ExperienceMemory.
"""

import json
import httpx
from typing import Dict, Any, Optional
from config import config
from brain.memory import memory_store


class TradeReflector:
    def __init__(self):
        self.api_key = config.jev_api_key
        self.endpoint = config.jev_api_endpoint
        self.model = config.jev_model

    async def reflect_on_trade(
        self,
        position: Dict[str, Any],
        exit_price: float,
        pnl: float,
        pnl_pct: float,
        exit_reason: str,
        current_indicators: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Conducts post-mortem reflection on a closed trade and stores it in memory.
        """
        entry_price = position.get("price", exit_price)
        trade_id = position.get("id", "TRADE")
        side = position.get("side", "BUY")
        is_win = pnl >= 0

        # Attempt to get LLM-driven reflection if API key is active
        lesson = None
        category = None

        if self.api_key and ("openrouter.ai" in self.endpoint or self.api_key.startswith("sk-or-")):
            try:
                lesson, category = await self._generate_llm_reflection(
                    position, exit_price, pnl, pnl_pct, exit_reason, current_indicators
                )
            except Exception as e:
                print(f"[TradeReflector] LLM reflection failed, using heuristic: {e}")

        # Fallback heuristic reflection
        if not lesson:
            lesson, category = self._generate_heuristic_reflection(
                position, exit_price, pnl, pnl_pct, exit_reason, current_indicators
            )

        recorded = memory_store.record_trade_reflection(
            trade_id=trade_id,
            side=side,
            entry_price=entry_price,
            exit_price=exit_price,
            pnl=pnl,
            pnl_pct=pnl_pct,
            lesson=lesson,
            mistake_category=category
        )

        return recorded

    async def _generate_llm_reflection(
        self,
        pos: Dict[str, Any],
        exit_p: float,
        pnl: float,
        pnl_pct: float,
        reason: str,
        ind: Optional[Dict[str, Any]]
    ):
        """Generates deep analytical reflection using AI model."""
        prompt = f"""Phân tích lệnh vừa kết thúc của cặp ARB/USDT:
- Giá vào: {pos.get('price'):.4f} USDT | Lý do vào: {pos.get('reason', 'BUY')}
- Giá thoát: {exit_p:.4f} USDT | Lý do thoát: {reason}
- Kết quả: {'THẮNG (LÃI)' if pnl >= 0 else 'THUA (LỖ)'} ${pnl:.2f} ({pnl_pct:+.2f}%)
- Chỉ báo lúc thoát: RSI={ind.get('rsi', 'N/A') if ind else 'N/A'}, Trend={ind.get('trend', 'N/A') if ind else 'N/A'}

Hãy rút ra ĐÚNG 1 BÀI HỌC HÀNH ĐỘNG (actionable lesson) cực kỳ súc tích dưới 35 từ bằng tiếng Việt để Jev AI không lặp lại sai lầm nếu thua, hoặc phát huy điểm tốt nếu thắng.
Trả về định dạng JSON: {{"category": "<tên danh mục ngắn>", "lesson": "<bài học súc tích>"}}"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://jevai.org",
            "X-Title": "Jev AI Post-Mortem Reflector",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model or "google/gemini-2.5-flash",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }

        target_url = self.endpoint if "openrouter.ai" in self.endpoint else "https://openrouter.ai/api/v1/chat/completions"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(target_url, json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                content = json.loads(data["choices"][0]["message"]["content"])
                return content.get("lesson"), content.get("category")
        return None, None

    def _generate_heuristic_reflection(
        self,
        pos: Dict[str, Any],
        exit_p: float,
        pnl: float,
        pnl_pct: float,
        reason: str,
        ind: Optional[Dict[str, Any]]
    ):
        """High-precision heuristic reflection generator."""
        ind = ind or {}
        rsi = ind.get("rsi", 50.0)

        if pnl >= 0:
            if "TAKE_PROFIT" in reason:
                return (
                    f"Chốt lời thành công +{pnl_pct:.2f}%. Bắt nhịp sóng tăng đúng đà và tuân thủ kỷ luật chốt lời theo ATR.",
                    "TAKE_PROFIT_SUCCESS"
                )
            elif "TRAILING" in reason:
                return (
                    f"Khóa lợi nhuận +{pnl_pct:.2f}% qua Trailing Stop. Cơ chế dời SL nâng dần đã bảo toàn thành quả khi đảo chiều.",
                    "TRAILING_STOP_LOCK"
                )
            else:
                return (
                    f"Giao dịch có lãi +{pnl_pct:.2f}%. Tín hiệu đảo chiều của Jev AI giúp thoát hàng kịp thời ở vùng giá tốt.",
                    "EARLY_EXIT_PROFIT"
                )
        else:
            if "STOP_LOSS" in reason:
                if rsi > 68:
                    return (
                        f"Lỗ {pnl_pct:.2f}% do dính bẫy giá Bull Trap khi RSI ở vùng quá mua ({rsi:.1f}). Cần tránh mở BUY khi RSI > 68.",
                        "OVERBOUGHT_BULL_TRAP"
                    )
                else:
                    return (
                        f"Cắt lỗ {pnl_pct:.2f}% bảo toàn vốn. Thị trường quét thanh khoản biên độ mạnh, cần kiên nhẫn chờ nến xác nhận đóng cửa.",
                        "STOP_LOSS_PROTECTION"
                    )
            else:
                return (
                    f"Thoát lệnh lỗ {pnl_pct:.2f}% theo tín hiệu SELL của Jev AI. Quyết định cắt lỗ chủ động giúp tránh mức giảm sâu hơn.",
                    "EARLY_RISK_MITIGATION"
                )

reflector = TradeReflector()
