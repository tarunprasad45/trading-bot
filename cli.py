"""
cli.py — Command-line interface for the trading bot.

Usage examples:

  # Market order (live)
  python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

  # Limit order (dry run — no real order sent)
  python cli.py --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.5 --price 3200 --dry-run
"""

from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.text import Text

from bot.exceptions import BinanceAPIError, NetworkError, ValidationError
from bot.orders import place_order
from bot.validators import validate_order

app = typer.Typer(
    name="trading-bot",
    help="Binance order execution CLI with pre-trade validation and dry-run mode.",
    add_completion=False,
)
console = Console()
err_console = Console(stderr=True, style="bold red")


def _render_summary(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float],
    dry_run: bool,
) -> Panel:
    """Renders the pre-trade order summary panel."""
    table = Table(box=None, show_header=False, padding=(0, 2))
    table.add_column("Field", style="dim")
    table.add_column("Value", style="bold white")

    table.add_row("Symbol", symbol)
    table.add_row("Side", f"[green]{side}[/green]" if side == "BUY" else f"[red]{side}[/red]")
    table.add_row("Type", order_type)
    table.add_row("Quantity", str(quantity))
    if price:
        table.add_row("Price", f"{price:,.2f}")
    mode_text = "[yellow]DRY RUN ⚠️[/yellow]" if dry_run else "[green]LIVE[/green]"
    table.add_row("Mode", mode_text)

    return Panel(
        table,
        title="[bold cyan]ORDER SUMMARY[/bold cyan]",
        border_style="cyan",
        box=box.ROUNDED,
    )


def _render_result(result) -> Panel:
    """Renders the post-execution result panel."""
    table = Table(box=None, show_header=False, padding=(0, 2))
    table.add_column("Field", style="dim")
    table.add_column("Value", style="bold white")

    if result.dry_run:
        table.add_row("Status", "[yellow]DRY RUN — order not submitted[/yellow]")
        table.add_row("Payload logged", "✓  (see logs/bot.log)")
    else:
        status_color = "green" if result.status in ("FILLED", "NEW") else "yellow"
        table.add_row("Status", f"[{status_color}]{result.status}[/{status_color}]")
        table.add_row("Order ID", str(result.order_id))
        if result.executed_qty is not None:
            table.add_row("Executed Qty", str(result.executed_qty))
        if result.avg_price:
            table.add_row("Avg Price", f"{result.avg_price:,.2f}")

    table.add_row("Latency", f"{result.latency_ms:.2f} ms")

    border = "yellow" if result.dry_run else "green"
    title = "[bold yellow]DRY RUN RESULT[/bold yellow]" if result.dry_run else "[bold green]ORDER PLACED[/bold green]"

    return Panel(table, title=title, border_style=border, box=box.ROUNDED)


@app.command()
def order(
    symbol: str = typer.Option(..., "--symbol", "-s", help="Trading pair, e.g. BTCUSDT"),
    side: str = typer.Option(..., "--side", help="BUY or SELL"),
    order_type: str = typer.Option(..., "--type", "-t", help="MARKET or LIMIT"),
    quantity: float = typer.Option(..., "--quantity", "-q", help="Base asset quantity"),
    price: Optional[float] = typer.Option(None, "--price", "-p", help="Limit price (required for LIMIT orders)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate order without sending to Binance"),
):
    """Place a MARKET or LIMIT order on Binance."""

    # --- Validate ---
    try:
        symbol, side, order_type, quantity, price = validate_order(
            symbol, side, order_type, quantity, price
        )
    except ValidationError as exc:
        err_console.print(f"\n[VALIDATION ERROR] {exc}\n")
        raise typer.Exit(code=1)

    # --- Show pre-trade summary ---
    console.print()
    console.print(_render_summary(symbol, side, order_type, quantity, price, dry_run))

    # --- Confirm if live ---
    if not dry_run:
        confirmed = typer.confirm("Submit this order?", default=False)
        if not confirmed:
            console.print("[dim]Order cancelled.[/dim]\n")
            raise typer.Exit(code=0)

    # --- Execute ---
    try:
        result = place_order(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            dry_run=dry_run,
        )
    except ValidationError as exc:
        err_console.print(f"\n[VALIDATION ERROR] {exc}\n")
        raise typer.Exit(code=1)
    except BinanceAPIError as exc:
        err_console.print(f"\n[BINANCE API ERROR] {exc}\n")
        raise typer.Exit(code=2)
    except NetworkError as exc:
        err_console.print(f"\n[NETWORK ERROR] {exc}\n")
        raise typer.Exit(code=3)

    # --- Show result ---
    console.print(_render_result(result))
    console.print()


if __name__ == "__main__":
    app()
