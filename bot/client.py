"""
client.py — Binance HTTP layer.

Single responsibility: send signed requests to the Binance REST API
and return parsed JSON. Everything else (business logic, validation,
CLI) lives in other modules.

Signing follows the Binance HMAC-SHA256 scheme:
  https://binance-docs.github.io/apidocs/spot/en/#signed-trade-endpoints
"""

import hashlib
import hmac
import time
from urllib.parse import urlencode

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import config
from bot.exceptions import BinanceAPIError, NetworkError
from bot.logger import get_logger

logger = get_logger(__name__)


class BinanceClient:
    """
    Reusable HTTP client for the Binance Spot REST API.

    Handles:
    - HMAC-SHA256 request signing
    - Automatic retries with exponential backoff (network errors only)
    - Per-request latency measurement
    - Structured logging of every request/response
    """

    def __init__(
        self,
        api_key: str = config.BINANCE_API_KEY,
        secret_key: str = config.BINANCE_SECRET_KEY,
        base_url: str = config.BINANCE_BASE_URL,
        timeout: int = config.REQUEST_TIMEOUT_SECONDS,
        max_retries: int = config.MAX_RETRIES,
    ):
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        self.session = requests.Session()
        retry = Retry(
            total=max_retries,
            backoff_factor=config.RETRY_BACKOFF_SECONDS,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST", "GET"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update({"X-MBX-APIKEY": self.api_key})

    # --- Internal helpers ---

    def _sign(self, params: dict) -> dict:
        """Append timestamp and HMAC-SHA256 signature to params."""
        params["timestamp"] = int(time.time() * 1000)
        query_string = urlencode(params)
        signature = hmac.new(
            self.secret_key.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    def _handle_response(self, response: requests.Response) -> dict:
        """Parse response JSON, raise BinanceAPIError on non-2xx."""
        try:
            data = response.json()
        except ValueError:
            raise BinanceAPIError(
                f"Non-JSON response from Binance: {response.text[:200]}",
                status_code=response.status_code,
            )

        if not response.ok:
            msg = data.get("msg", "Unknown Binance error")
            code = data.get("code")
            raise BinanceAPIError(msg, status_code=response.status_code, error_code=code)

        return data

    # --- Public interface ---

    def post(self, endpoint: str, params: dict) -> tuple[dict, float]:
        """
        Send a signed POST request.

        Returns:
            (response_dict, latency_ms)
        Raises:
            BinanceAPIError  — API-level error
            NetworkError     — connection / timeout
        """
        url = f"{self.base_url}{endpoint}"
        signed_params = self._sign(params.copy())

        logger.debug({
            "event": "REQUEST",
            "method": "POST",
            "url": url,
            "params": {k: v for k, v in params.items()
                       if k not in ("signature",)},
        })

        t_start = time.perf_counter()
        try:
            response = self.session.post(
                url, data=signed_params, timeout=self.timeout
            )
        except requests.exceptions.Timeout:
            raise NetworkError(f"Request to {url} timed out after {self.timeout}s.")
        except requests.exceptions.ConnectionError as exc:
            raise NetworkError(f"Connection error: {exc}")
        finally:
            latency_ms = (time.perf_counter() - t_start) * 1000

        data = self._handle_response(response)

        logger.debug({
            "event": "RESPONSE",
            "status_code": response.status_code,
            "latency_ms": round(latency_ms, 3),
        })

        return data, latency_ms
