"""
Main Entry Point for Jev AI Binance ARB/USDT Trading System.
"""

import sys
import uvicorn

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import config
from version import get_version

def main():
    print("=" * 60)
    print("   ⚡ JEV AI - BINANCE ARB/USDT TRADING SYSTEM ⚡")
    print(f"   Version: {get_version()} | Brain: jevai.org (System One)")
    print(f"   Trading Mode: {config.trading_mode} | Pair: {config.symbol}")
    print(f"   Dashboard Web UI: http://{config.web_host}:{config.web_port}")
    print("=" * 60)

    uvicorn.run(
        "server.api:app",
        host=config.web_host,
        port=config.web_port,
        log_level="info",
        reload=False
    )

if __name__ == "__main__":
    main()
