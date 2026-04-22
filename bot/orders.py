"""
orders.py — Order placement business logic.

This layer sits between the CLI and the HTTP client. It:
- Builds the correct Binance API payload for each order type
- Delegates signing + transport to BinanceClient
- Measures and logs execution latency
- Supports dry-run mode (simulate without sending)

Nothing here touches the terminal or does input validation —
those responsibilities live in cli.py and validators.py respectively.
"""

import time
from dataclasses import dataclass
from typing import Optional

from bot.client import BinanceClient
from bot.logger import get_logger

logger = get_logger(__name__)

ORDER_ENDPOINT = "/v3/order"


@dataclass
class OrderResult:
    """
    Normalised order result.
    Works for both live fills and dry-run simulations.
    """
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float]
    dry_run: bool

    # Fields populated after a live fill
    order_id: Optional[int] = None
    status: Optional[str] = None
    executed_qty: Optional[float] = None
    avg_price: Optional[float] = None
    latency_ms: Optional[float] = None

    # Raw API payload (dry-run) or raw API response (live)
    raw: Optional[dict] = None

# NOTE:
# This assumes Binance Spot API format.
# Futures or advanced order types would require additional fields.

def _build_payload(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float],
) -> dict:
    payload = {
        "symbol": symbol,
        "side": side,
        "type": order_type,
        "quantity": quantity,
    }
    if order_type == "LIMIT":
        payload["price"] = price
        payload["timeInForce"] = "GTC"   # Good-Till-Cancelled — standard default
    return payload


def place_order(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float] = None,
    dry_run: bool = False,
    client: Optional[BinanceClient] = None,
) -> OrderResult:
    """
    Place a MARKET or LIMIT order.

    Args:
        symbol:     Trading pair, e.g. 'BTCUSDT'
        side:       'BUY' or 'SELL'
        order_type: 'MARKET' or 'LIMIT'
        quantity:   Base asset quantity
        price:      Required for LIMIT, ignored for MARKET
        dry_run:    If True, log the payload but do NOT send to Binance
        client:     Injected BinanceClient (defaults to a fresh one)

    Returns:
        OrderResult
    """
    payload = _build_payload(symbol, side, order_type, quantity, price)

    if dry_run:
        t_start = time.perf_counter()
        latency_ms = (time.perf_counter() - t_start) * 1000  # ~0 — intentional

        logger.info({
            "event": "DRY_RUN",
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
            "price": price,
            "latency_ms": round(latency_ms, 3),
            "payload": payload,
        })

        return OrderResult(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            dry_run=True,
            status="DRY_RUN",
            latency_ms=round(latency_ms, 3),
            raw=payload,
        )

    # --- Live order ---
    if client is None:
        client = BinanceClient()

    logger.info({
        "event": "ORDER_REQUEST",
        "symbol": symbol,
        "side": side,
        "type": order_type,
        "quantity": quantity,
        "price": price,
    })

    response, latency_ms = client.post(ORDER_ENDPOINT, payload)

    result = OrderResult(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price,
        dry_run=False,
        order_id=response.get("orderId"),
        status=response.get("status"),
        executed_qty=float(response.get("executedQty", 0)),
        avg_price=float(response.get("fills", [{}])[0].get("price", 0))
                  if response.get("fills") else None,
        latency_ms=round(latency_ms, 3),
        raw=response,
    )

    logger.info({
        "event": "ORDER_PLACED",
        "orderId": result.order_id,
        "status": result.status,
        "executedQty": result.executed_qty,
        "avgPrice": result.avg_price,
        "latency_ms": result.latency_ms,
    })

    return result



def place_market_order(
    symbol: str, side: str, quantity: float,
    dry_run: bool = False, client: Optional[BinanceClient] = None,
) -> OrderResult:
    return place_order(symbol, side, "MARKET", quantity,
                       dry_run=dry_run, client=client)


def place_limit_order(
    symbol: str, side: str, quantity: float, price: float,
    dry_run: bool = False, client: Optional[BinanceClient] = None,
) -> OrderResult:
    return place_order(symbol, side, "LIMIT", quantity, price,
                       dry_run=dry_run, client=client)
