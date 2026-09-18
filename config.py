import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load .env file from project root
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

class BotConfig(BaseModel):
    # Jev AI Config
    jev_api_key: str = Field(default_factory=lambda: os.getenv("JEV_API_KEY", ""))
    jev_api_endpoint: str = Field(default_factory=lambda: os.getenv("JEV_API_ENDPOINT", "https://api.typesafe.ai/v1/systemone"))
    jev_model: str = Field(default_factory=lambda: os.getenv("JEV_MODEL", "jev-1"))
    jev_enable_emulator_fallback: bool = Field(
        default_factory=lambda: os.getenv("JEV_ENABLE_EMULATOR_FALLBACK", "true").lower() in ("true", "1", "yes")
    )
    
    # Binance Config
    binance_api_key: str = Field(default_factory=lambda: os.getenv("BINANCE_API_KEY", ""))
    binance_api_secret: str = Field(default_factory=lambda: os.getenv("BINANCE_API_SECRET", ""))
    binance_market_type: str = Field(default_factory=lambda: os.getenv("BINANCE_MARKET_TYPE", "SPOT").upper())
    binance_testnet: bool = Field(
        default_factory=lambda: os.getenv("BINANCE_TESTNET", "false").lower() in ("true", "1", "yes")
    )
    
    # Trading Pair & Mode
    symbol: str = Field(default_factory=lambda: os.getenv("SYMBOL", "ARB/USDT"))
    trading_mode: str = Field(default_factory=lambda: os.getenv("TRADING_MODE", "PAPER").upper())
    paper_initial_balance: float = Field(default_factory=lambda: float(os.getenv("PAPER_INITIAL_BALANCE", "1000.0")))
    
    # Risk Guardian
    risk_per_trade_percent: float = Field(default_factory=lambda: float(os.getenv("RISK_PER_TRADE_PERCENT", "1.5")))
    min_jev_confidence: int = Field(default_factory=lambda: int(os.getenv("MIN_JEV_CONFIDENCE", "75")))
    atr_sl_multiplier: float = Field(default_factory=lambda: float(os.getenv("ATR_SL_MULTIPLIER", "1.8")))
    atr_tp_multiplier: float = Field(default_factory=lambda: float(os.getenv("ATR_TP_MULTIPLIER", "3.0")))
    max_daily_drawdown_percent: float = Field(default_factory=lambda: float(os.getenv("MAX_DAILY_DRAWDOWN_PERCENT", "5.0")))
    trailing_stop_enabled: bool = Field(
        default_factory=lambda: os.getenv("TRAILING_STOP_ENABLED", "true").lower() in ("true", "1", "yes")
    )
    trailing_stop_callback_percent: float = Field(
        default_factory=lambda: float(os.getenv("TRAILING_STOP_CALLBACK_PERCENT", "0.8"))
    )
    
    # Web Terminal
    web_host: str = Field(default_factory=lambda: os.getenv("WEB_HOST", "127.0.0.1"))
    web_port: int = Field(default_factory=lambda: int(os.getenv("WEB_PORT", "8080")))

config = BotConfig()
