"""
Binance Client and Paper Trading Simulator Engine.
Handles real-time Binance API connectivity via CCXT and provides a high-fidelity Paper Trading engine.
"""

import time
import asyncio
from typing import Dict, Any, List, Optional
import ccxt
import pandas as pd
from config import config


class BinanceClient:
    def __init__(self):
        self.symbol = config.symbol
        self.market_type = config.binance_market_type
        self.is_paper = config.trading_mode == "PAPER"
        self.testnet = config.binance_testnet
        
        # CCXT Exchange Instance
        exchange_class = ccxt.binance if self.market_type == "SPOT" else ccxt.binanceusdm
        exchange_params: Dict[str, Any] = {
            "enableRateLimit": True,
            "options": {"defaultType": "spot" if self.market_type == "SPOT" else "future"}
        }

        if not self.is_paper and config.binance_api_key and config.binance_api_secret:
            exchange_params["apiKey"] = config.binance_api_key
            exchange_params["secret"] = config.binance_api_secret

        self.exchange = exchange_class(exchange_params)
        if self.testnet:
            self.exchange.set_sandbox_mode(True)

        # Paper Trading Virtual State
        self.paper_usdt = float(config.paper_initial_balance)
        self.paper_arb = 0.0
        self.paper_initial_capital = float(config.paper_initial_balance)
        self.paper_trades: List[Dict[str, Any]] = []
        self.paper_open_position: Optional[Dict[str, Any]] = None

    def get_ticker(self) -> Dict[str, Any]:
        """Fetch real-time ticker data for ARB/USDT from Binance."""
        try:
            ticker = self.exchange.fetch_ticker(self.symbol)
            return {
                "symbol": self.symbol,
                "price": float(ticker["last"]),
                "bid": float(ticker["bid"]) if ticker["bid"] else float(ticker["last"]),
                "ask": float(ticker["ask"]) if ticker["ask"] else float(ticker["last"]),
                "percentage_24h": float(ticker.get("percentage", 0.0)),
                "volume_24h": float(ticker.get("quoteVolume", 0.0)),
                "timestamp": int(ticker.get("timestamp", time.time() * 1000))
            }
        except Exception as e:
            # Fallback in case of temporary network issue
            return {
                "symbol": self.symbol,
                "price": 0.50,
                "bid": 0.499,
                "ask": 0.501,
                "percentage_24h": 0.0,
                "volume_24h": 0.0,
                "timestamp": int(time.time() * 1000),
                "error": str(e)
            }

    def get_ohlcv(self, timeframe: str = "5m", limit: int = 100) -> pd.DataFrame:
        """Fetch historical candles from Binance."""
        try:
            raw_candles = self.exchange.fetch_ohlcv(self.symbol, timeframe=timeframe, limit=limit)
            df = pd.DataFrame(raw_candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
            return df
        except Exception as e:
            print(f"[BinanceClient] Error fetching OHLCV: {e}")
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

    def get_order_book(self, limit: int = 20) -> Dict[str, Any]:
        """Fetch order book depth and compute bid/ask ratio."""
        try:
            order_book = self.exchange.fetch_order_book(self.symbol, limit=limit)
            bids = order_book["bids"]
            asks = order_book["asks"]

            bid_vol = sum([b[1] for b in bids]) if bids else 0.0
            ask_vol = sum([a[1] for a in asks]) if asks else 0.0
            spread = (asks[0][0] - bids[0][0]) if (bids and asks) else 0.0
            spread_pct = (spread / bids[0][0] * 100) if (bids and bids[0][0] > 0) else 0.0

            ratio = (bid_vol / ask_vol) if ask_vol > 0 else 1.0

            return {
                "top_bid": bids[0][0] if bids else 0.0,
                "top_ask": asks[0][0] if asks else 0.0,
                "bid_volume": round(bid_vol, 2),
                "ask_volume": round(ask_vol, 2),
                "bid_ask_ratio": round(ratio, 3),
                "spread": round(spread, 5),
                "spread_pct": round(spread_pct, 3)
            }
        except Exception as e:
            return {
                "top_bid": 0.0,
                "top_ask": 0.0,
                "bid_volume": 0.0,
                "ask_volume": 0.0,
                "bid_ask_ratio": 1.0,
                "spread": 0.0,
                "spread_pct": 0.0,
                "error": str(e)
            }

    def get_balance(self, current_price: Optional[float] = None) -> Dict[str, Any]:
        """Returns account balance (paper or live)."""
        if current_price is None or current_price <= 0:
            ticker = self.get_ticker()
            current_price = ticker["price"]

        if self.is_paper:
            arb_value = self.paper_arb * current_price
            total_equity = self.paper_usdt + arb_value
            total_pnl = total_equity - self.paper_initial_capital
            total_pnl_pct = (total_pnl / self.paper_initial_capital) * 100

            return {
                "mode": "PAPER",
                "usdt_free": round(self.paper_usdt, 2),
                "arb_free": round(self.paper_arb, 4),
                "arb_value_usdt": round(arb_value, 2),
                "total_equity": round(total_equity, 2),
                "total_pnl": round(total_pnl, 2),
                "total_pnl_pct": round(total_pnl_pct, 2)
            }
        else:
            try:
                balance = self.exchange.fetch_balance()
                usdt_free = float(balance["USDT"]["free"]) if "USDT" in balance else 0.0
                arb_free = float(balance["ARB"]["free"]) if "ARB" in balance else 0.0
                arb_val = arb_free * current_price
                total_equity = usdt_free + arb_val

                return {
                    "mode": "LIVE",
                    "usdt_free": round(usdt_free, 2),
                    "arb_free": round(arb_free, 4),
                    "arb_value_usdt": round(arb_val, 2),
                    "total_equity": round(total_equity, 2),
                    "total_pnl": 0.0,
                    "total_pnl_pct": 0.0
                }
            except Exception as e:
                return {
                    "mode": "LIVE_ERROR",
                    "error": str(e),
                    "usdt_free": 0.0,
                    "arb_free": 0.0,
                    "total_equity": 0.0
                }

    def execute_paper_order(self, side: str, amount_usdt: float, price: float,
                            stop_loss: float, take_profit: float, reason: str = "") -> Dict[str, Any]:
        """Execute simulated trade in Paper Trading mode."""
        fee_rate = 0.001  # 0.1% standard Binance fee
        
        if side == "BUY":
            if amount_usdt > self.paper_usdt:
                amount_usdt = self.paper_usdt * 0.98  # allocate 98% of available

            if amount_usdt < 5.0:
                return {"status": "REJECTED", "reason": "Insufficient USDT balance (< $5)"}

            fee = amount_usdt * fee_rate
            net_usdt = amount_usdt - fee
            arb_bought = net_usdt / price

            self.paper_usdt -= amount_usdt
            self.paper_arb += arb_bought

            order_record = {
                "id": f"PAPER-{int(time.time()*1000)}",
                "timestamp": int(time.time() * 1000),
                "symbol": self.symbol,
                "side": "BUY",
                "price": price,
                "amount_arb": arb_bought,
                "amount_usdt": amount_usdt,
                "fee": fee,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "highest_price": price,  # for trailing stop
                "reason": reason,
                "status": "OPEN"
            }
            self.paper_open_position = order_record
            self.paper_trades.append(order_record)
            return {"status": "SUCCESS", "order": order_record}

        elif side == "SELL":
            if self.paper_arb <= 0:
                return {"status": "REJECTED", "reason": "No ARB holdings to sell"}

            arb_to_sell = self.paper_arb
            gross_usdt = arb_to_sell * price
            fee = gross_usdt * fee_rate
            net_usdt = gross_usdt - fee

            entry_price = self.paper_open_position["price"] if self.paper_open_position else price
            pnl = (price - entry_price) * arb_to_sell - fee
            pnl_pct = ((price - entry_price) / entry_price) * 100 if entry_price > 0 else 0.0

            self.paper_usdt += net_usdt
            self.paper_arb = 0.0

            order_record = {
                "id": f"PAPER-{int(time.time()*1000)}",
                "timestamp": int(time.time() * 1000),
                "symbol": self.symbol,
                "side": "SELL",
                "price": price,
                "amount_arb": arb_to_sell,
                "amount_usdt": net_usdt,
                "fee": fee,
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct, 2),
                "reason": reason,
                "status": "CLOSED"
            }
            self.paper_open_position = None
            self.paper_trades.append(order_record)
            return {"status": "SUCCESS", "order": order_record}

        return {"status": "INVALID_SIDE"}

    def close_all_positions(self, current_price: Optional[float] = None) -> Dict[str, Any]:
        """Emergency Close All Positions."""
        if current_price is None:
            current_price = self.get_ticker()["price"]

        if self.is_paper:
            if self.paper_arb > 0:
                return self.execute_paper_order(
                    side="SELL",
                    amount_usdt=0,
                    price=current_price,
                    stop_loss=0,
                    take_profit=0,
                    reason="EMERGENCY_CLOSE_ALL"
                )
            return {"status": "NO_POSITION"}
        else:
            try:
                # Live market sell
                balance = self.exchange.fetch_balance()
                arb_free = float(balance["ARB"]["free"]) if "ARB" in balance else 0.0
                if arb_free > 1.0:
                    order = self.exchange.create_market_sell_order(self.symbol, arb_free)
                    return {"status": "SUCCESS", "order": order}
                return {"status": "NO_POSITION"}
            except Exception as e:
                return {"status": "ERROR", "error": str(e)}
