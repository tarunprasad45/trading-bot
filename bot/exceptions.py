class TradingBotError(Exception):
    """Base exception for all trading bot errors"""
    pass

class ValidationError(TradingBotError):
    """Raised when input validation fails."""
    pass


class BinanceAPIError(TradingBotError):
    """Raised when the Binance API returns an error."""

    def __init__(self, message: str, status_code: int = None, error_code: int = None):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code

    def __str__(self):
        parts = [super().__str__()]
        if self.status_code:
            parts.append(f"HTTP {self.status_code}")
        if self.error_code:
            parts.append(f"Binance code {self.error_code}")
        return " | ".join(parts)

class NetworkError(TradingBotError):
    """Raised when a network/connectivity issue occurs."""
    pass

