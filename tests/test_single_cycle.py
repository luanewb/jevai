import asyncio
import sys
from pathlib import Path

# Ensure UTF-8 output
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to sys.path
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from execution.trader import coordinator

async def run_single_cycle():
    print("Testing single cycle of TradingCoordinator...")
    # Fetch ticker & order book
    ticker = coordinator.binance.get_ticker()
    print("1. Ticker ARB/USDT:", ticker["price"])

    order_book = coordinator.binance.get_order_book()
    print("2. Order Book Bid/Ask Ratio:", order_book["bid_ask_ratio"])

    # Fetch OHLCV & indicators
    df = coordinator.binance.get_ohlcv("5m", 100)
    ind = coordinator.indicators_calc.calculate_all(df)
    print(f"3. Indicators: RSI={ind['rsi']}, MACD={ind['macd_hist']}, Trend={ind['trend']}")

    balance = coordinator.binance.get_balance(ticker["price"])
    print(f"4. Balance: Total Equity=${balance['total_equity']}, USDT=${balance['usdt_free']}")

    # Build state
    state = coordinator.state_builder.build_state(ticker, ind, order_book, balance, None)
    print("5. State built successfully (length:", len(state), "chars)")

    # Query Jev AI
    decision = await coordinator.jev.decide(state, ind, False)
    print("6. Jev AI Decision:")
    print("   Action:", decision.action)
    print("   Confidence:", decision.confidence, "%")
    print("   Probability:", decision.action_prob)
    print("   Regime:", decision.regime)
    print("   Reasoning:", decision.reasoning)
    print("   Latency:", decision.latency_ms, "ms")

    # Risk eval
    eval_res = coordinator.risk.evaluate_entry(decision, ticker["price"], ind["atr"], balance)
    print("7. Risk Evaluation Approved:", eval_res["approved"])

    print("\nSUCCESS: All pipeline components operational!")

if __name__ == "__main__":
    asyncio.run(run_single_cycle())
