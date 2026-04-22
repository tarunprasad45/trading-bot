# Trading Bot — Binance Order Execution CLI

A clean, production-style CLI for placing spot orders on Binance.
Built with separation of concerns, pre-trade validation, dry-run simulation, and structured logging.

---

## Setup

```bash
git clone [<repo-url>](https://github.com/tarunprasad45/trading-bot.git) && cd trading_bot
pip install -r requirements.txt
```

Copy the example env file and add your credentials:

```bash
cp .env.example .env
# Edit .env — add your Binance Testnet API keys
```

Get free testnet keys at [testnet.binance.vision](https://testnet.binance.vision/).
The bot defaults to testnet — no real funds are used unless you change `BINANCE_BASE_URL`.

---

## Usage

### Market Order

```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
```

### Limit Order

```bash
python cli.py --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.5 --price 3200
```

### Dry Run (simulate without sending)

Append `--dry-run` to any command:

```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01 --dry-run
```

---

## Sample Output

**Dry run:**

```
╭─────────────────────────────────╮
│         ORDER SUMMARY           │
│  Symbol    BTCUSDT              │
│  Side      BUY                  │
│  Type      MARKET               │
│  Quantity  0.01                 │
│  Mode      DRY RUN ⚠️           │
╰─────────────────────────────────╯

╭──────────────────────────────────────╮
│           DRY RUN RESULT             │
│  Status      DRY RUN — not submitted │
│  Payload     ✓  (see logs/bot.log)   │
│  Latency     0.04 ms                 │
╰──────────────────────────────────────╯
```

**Live fill:**

```
╭─────────────────────────────────╮
│         ORDER SUMMARY           │
│  Symbol    BTCUSDT              │
│  Side      BUY                  │
│  Type      MARKET               │
│  Quantity  0.01                 │
│  Mode      LIVE                 │
╰─────────────────────────────────╯

Submit this order? [y/N]: y

╭────────────────────────╮
│      ORDER PLACED      │
│  Status      FILLED    │
│  Order ID    12345678  │
│  Executed    0.01      │
│  Avg Price   64,021.00 │
│  Latency     183.42 ms │
╰────────────────────────╯
```

---

## Sample Log (`logs/bot.log`)

Every event is a single-line JSON object — easy to grep, pipe, or ingest:

```json
{"ts": "2026-04-22T07:51:41.460077+00:00", "level": "INFO", "logger": "bot.orders", "event": "DRY_RUN", "symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quantity": 0.01, "price": null, "latency_ms": 0.0, "payload": {"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quantity": 0.01}}
{"ts": "2026-04-22T07:51:44.563888+00:00", "level": "INFO", "logger": "bot.orders", "event": "DRY_RUN", "symbol": "ETHUSDT", "side": "SELL", "type": "LIMIT", "quantity": 0.5, "price": 3200.0, "latency_ms": 0.0, "payload": {"symbol": "ETHUSDT", "side": "SELL", "type": "LIMIT", "quantity": 0.5, "price": 3200.0, "timeInForce": "GTC"}}
```

For a live fill, the log will contain `ORDER_REQUEST` then `ORDER_PLACED`:

```json
{"ts": "2026-04-22T10:23:01.412Z", "level": "INFO", "logger": "bot.orders", "event": "ORDER_REQUEST", "symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quantity": 0.01, "price": null}
{"ts": "2026-04-22T10:23:01.596Z", "level": "INFO", "logger": "bot.orders", "event": "ORDER_PLACED", "orderId": 12345678, "status": "FILLED", "executedQty": 0.01, "avgPrice": 64021.0, "latency_ms": 183.42}
```

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── client.py       # HTTP layer — signing, retries, transport
│   ├── orders.py       # Business logic — place_market_order, place_limit_order
│   ├── validators.py   # Input validation — runs before any API call
│   ├── exceptions.py   # Custom errors — BinanceAPIError, ValidationError, NetworkError
│   └── logger.py       # Structured JSON logging — file + stderr
├── cli.py              # Typer CLI with Rich terminal output
├── config.py           # Environment config via python-dotenv
├── requirements.txt
├── .env.example
└── logs/
    └── bot.log         # Generated at runtime
```

---

## Design Considerations

This project treats the CLI as an interface to an execution system, not just an API wrapper.

**Pre-trade validation** runs before any network call — symbols, sides, types, quantities, and price requirements are all checked at the boundary.

**Dry-run mode** simulates order placement end-to-end: the payload is built, logged, and returned without touching the exchange. Useful for testing integration without risking funds — a standard safeguard in real execution systems.

**Structured JSON logging** records every request, response, and error as a machine-readable object. This makes logs trivially greppable and ingestable by any downstream tooling.

**Per-request latency tracking** (`latency_ms`) is measured at the transport layer and surfaced in both the log and the terminal. Latency awareness is a baseline requirement for any system that eventually needs to compete on execution.

**Retry logic** handles transient network errors and rate-limit responses (429, 5xx) with exponential backoff. Application errors (4xx) are not retried — they surface immediately as `BinanceAPIError`.

---

## Assumptions

- Binance Testnet is the default target. Switch `BINANCE_BASE_URL` in `.env` for mainnet.
- `timeInForce` for LIMIT orders is `GTC` (Good-Till-Cancelled) — the standard default.
- The `executedQty` and `avgPrice` fields are parsed from the first fill in the API response. For partial fills, only the first fill price is shown in the terminal; the full response is available in the log.


