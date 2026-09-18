"""
Technical Analysis and Indicator Engine for ARB/USDT.
Computes EMA Ribbon, RSI, MACD, Bollinger Bands, ATR, and Volume metrics.
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd


class TechnicalIndicators:
    @staticmethod
    def calculate_all(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Takes an OHLCV DataFrame with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume'].
        Returns calculated indicators and latest metrics dictionary.
        """
        if df.empty or len(df) < 50:
            return {}

        df = df.copy()

        # 1. Exponential Moving Averages (EMA Ribbon)
        df["ema9"] = df["close"].ewm(span=9, adjust=False).mean()
        df["ema21"] = df["close"].ewm(span=21, adjust=False).mean()
        df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()
        if len(df) >= 200:
            df["ema200"] = df["close"].ewm(span=200, adjust=False).mean()
        else:
            df["ema200"] = df["close"].ewm(span=len(df), adjust=False).mean()

        # 2. RSI (14)
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-9)
        df["rsi"] = 100 - (100 / (1 + rs))

        # 3. MACD (12, 26, 9)
        ema12 = df["close"].ewm(span=12, adjust=False).mean()
        ema26 = df["close"].ewm(span=26, adjust=False).mean()
        df["macd"] = ema12 - ema26
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
        df["macd_hist"] = df["macd"] - df["macd_signal"]

        # 4. Bollinger Bands (20, 2)
        df["bb_middle"] = df["close"].rolling(window=20).mean()
        bb_std = df["close"].rolling(window=20).std()
        df["bb_upper"] = df["bb_middle"] + (2 * bb_std)
        df["bb_lower"] = df["bb_middle"] - (2 * bb_std)
        df["bb_bandwidth"] = (df["bb_upper"] - df["bb_lower"]) / (df["bb_middle"] + 1e-9)

        # 5. ATR (14) Average True Range
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift()).abs()
        low_close = (df["low"] - df["close"].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df["atr"] = tr.rolling(window=14).mean()

        # 6. Volume metrics
        df["vol_sma20"] = df["volume"].rolling(window=20).mean()
        df["vol_ratio"] = df["volume"] / (df["vol_sma20"] + 1e-9)

        # Extract latest values
        last = df.iloc[-1]
        prev = df.iloc[-2]

        current_price = float(last["close"])
        ema9_val = float(last["ema9"])
        ema21_val = float(last["ema21"])
        ema50_val = float(last["ema50"])
        ema200_val = float(last["ema200"])
        rsi_val = float(last["rsi"]) if not np.isnan(last["rsi"]) else 50.0
        macd_val = float(last["macd"])
        macd_sig_val = float(last["macd_signal"])
        macd_hist_val = float(last["macd_hist"])
        atr_val = float(last["atr"]) if not np.isnan(last["atr"]) else (current_price * 0.02)
        vol_ratio = float(last["vol_ratio"]) if not np.isnan(last["vol_ratio"]) else 1.0

        # Divergence / Crossover Signals
        macd_crossover = (prev["macd"] <= prev["macd_signal"]) and (last["macd"] > last["macd_signal"])
        macd_crossunder = (prev["macd"] >= prev["macd_signal"]) and (last["macd"] < last["macd_signal"])
        ema_bullish_alignment = ema9_val > ema21_val > ema50_val
        ema_bearish_alignment = ema9_val < ema21_val < ema50_val
        
        # Determine Market Trend
        if current_price > ema50_val and ema_bullish_alignment:
            trend = "BULLISH"
        elif current_price < ema50_val and ema_bearish_alignment:
            trend = "BEARISH"
        else:
            trend = "RANGING/NEUTRAL"

        return {
            "price": current_price,
            "ema9": ema9_val,
            "ema21": ema21_val,
            "ema50": ema50_val,
            "ema200": ema200_val,
            "rsi": round(rsi_val, 2),
            "macd": round(macd_val, 5),
            "macd_signal": round(macd_sig_val, 5),
            "macd_hist": round(macd_hist_val, 5),
            "macd_crossover": bool(macd_crossover),
            "macd_crossunder": bool(macd_crossunder),
            "bb_upper": round(float(last["bb_upper"]), 4),
            "bb_lower": round(float(last["bb_lower"]), 4),
            "bb_bandwidth": round(float(last["bb_bandwidth"]), 4),
            "atr": round(atr_val, 5),
            "volume_ratio": round(vol_ratio, 2),
            "trend": trend,
            "timestamp": int(last["timestamp"])
        }
