import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent/".env")

BINANCE_API_KEY: str = os.getenv("BINANCE_API_KEY", "")
BINANCE_SECRET_KEY: str = os.getenv("BINANCE_SECRET_KEY", "")
BINANCE_BASE_URL: str = os.getenv(
    "BINANCE_BASE_URL", "https://testnet.binance.vision/api"
)

# HTTP behaviour
REQUEST_TIMEOUT_SECONDS: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "10"))
MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
RETRY_BACKOFF_SECONDS: float = float(os.getenv("RETRY_BACKOFF_SECONDS", "1.0"))
