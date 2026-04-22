import re
from .exceptions import ValidationError

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT"}

# Binance symbol format: uppercase letters only, e.g. BTCUSDT
_SYMBOL_RE = re.compile(r"^[A-Z]{2,20}$")


def validate_symbol(symbol: str) -> str:
    s = symbol.strip().upper()
    if not _SYMBOL_RE.match(s):
        raise ValidationError(
            f"Invalid symbol '{symbol}'. Expected uppercase letters only (e.g. BTCUSDT)."
        )
    return s


def validate_side(side: str) -> str:
    s = side.strip().upper()
    if s not in VALID_SIDES:
        raise ValidationError(
            f"Invalid side '{side}'. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )
    return s


def validate_order_type(order_type: str) -> str:
    t = order_type.strip().upper()
    if t not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Invalid order type '{order_type}'. Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return t


def validate_quantity(quantity: float) -> float:
    if quantity <= 0:
        raise ValidationError(
            f"Quantity must be greater than 0, got {quantity}."
        )
    return quantity


def validate_price(price: float | None, order_type: str) -> float | None:
    if order_type == "LIMIT":
        if price is None:
            raise ValidationError("LIMIT orders require a --price argument.")
        if price <= 0:
            raise ValidationError(
                f"Price must be greater than 0, got {price}."
            )
    if order_type == "MARKET" and price is not None:
        # Not fatal — just ignore it — but warn the caller
        pass
    return price


def validate_order(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: float | None,
) -> tuple[str, str, str, float, float | None]:
    """
    Runs all validations in sequence and returns cleaned, normalised values.
    Raises ValidationError on the first failure found.
    """
    symbol = validate_symbol(symbol)
    side = validate_side(side)
    order_type = validate_order_type(order_type)
    quantity = validate_quantity(quantity)
    price = validate_price(price, order_type)
    return symbol, side, order_type, quantity, price


