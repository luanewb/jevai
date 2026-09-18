"""
State Builder for Jev AI (jevai.org / TypeSafe System One Model).
Serializes market data, technical indicators, order book depth, and current portfolio state
into a clean, information-dense context state for Jev AI decision making.
"""

from typing import Dict, Any, Optional


class JevStateBuilder:
    @staticmethod
    def build_state(
        ticker: Dict[str, Any],
        indicators: Dict[str, Any],
        order_book: Dict[str, Any],
        balance: Dict[str, Any],
        open_position: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Builds a comprehensive state representation string for Jev AI.
        """
        price = ticker.get("price", 0.0)
        pct_24h = ticker.get("percentage_24h", 0.0)
        vol_24h = ticker.get("volume_24h", 0.0)

        # Technical indicator summary
        trend = indicators.get("trend", "UNKNOWN")
        rsi = indicators.get("rsi", 50.0)
        macd = indicators.get("macd", 0.0)
        macd_signal = indicators.get("macd_signal", 0.0)
        macd_hist = indicators.get("macd_hist", 0.0)
        macd_cross = indicators.get("macd_crossover", False)
        ema9 = indicators.get("ema9", 0.0)
        ema21 = indicators.get("ema21", 0.0)
        ema50 = indicators.get("ema50", 0.0)
        ema200 = indicators.get("ema200", 0.0)
        atr = indicators.get("atr", price * 0.02)
        bb_upper = indicators.get("bb_upper", 0.0)
        bb_lower = indicators.get("bb_lower", 0.0)
        bb_bw = indicators.get("bb_bandwidth", 0.0)
        vol_ratio = indicators.get("volume_ratio", 1.0)

        # Order book summary
        bid_ask_ratio = order_book.get("bid_ask_ratio", 1.0)
        spread_pct = order_book.get("spread_pct", 0.0)

        # Account / Position summary
        equity = balance.get("total_equity", 1000.0)
        usdt_free = balance.get("usdt_free", 1000.0)
        
        pos_str = "NONE (Flat, ready for entry)"
        if open_position:
            entry_p = open_position.get("price", price)
            amt = open_position.get("amount_arb", 0.0)
            sl = open_position.get("stop_loss", 0.0)
            tp = open_position.get("take_profit", 0.0)
            pnl_pct = ((price - entry_p) / entry_p * 100) if entry_p > 0 else 0.0
            pos_str = (
                f"LONG {amt:.2f} ARB @ {entry_p:.4f} USDT | "
                f"Unrealized PnL: {pnl_pct:+.2f}% | SL: {sl:.4f} | TP: {tp:.4f}"
            )

        state = f"""[MARKET: ARB/USDT on Binance]
- Current Price: {price:.4f} USDT | 24h Change: {pct_24h:+.2f}% | 24h Quote Vol: ${vol_24h:,.0f}
- Trend Regime: {trend} (Price vs EMA50: {price - ema50:+.4f})
- Moving Averages: EMA9={ema9:.4f}, EMA21={ema21:.4f}, EMA50={ema50:.4f}, EMA200={ema200:.4f}
- Momentum: RSI(14)={rsi:.1f}, MACD={macd:+.5f}, Signal={macd_signal:+.5f}, Hist={macd_hist:+.5f} (Bullish Crossover: {macd_cross})
- Volatility & Bands: ATR(14)={atr:.5f} ({atr/price*100:.2f}%), BB Upper={bb_upper:.4f}, Lower={bb_lower:.4f}, Bandwidth={bb_bw:.4f}
- Liquidity & Flow: Vol Ratio={vol_ratio:.2f}x SMA20, Orderbook Bid/Ask Ratio={bid_ask_ratio:.2f}, Spread={spread_pct:.3f}%
- Portfolio Status: Available USDT={usdt_free:.2f}, Total Equity={equity:.2f} USDT
- Active Position: {pos_str}
"""
        return state.strip()
