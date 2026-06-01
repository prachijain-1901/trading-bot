"""
cli.py — Command-line interface for the Binance Futures Trading Bot.

Usage examples
--------------
# Market buy
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

# Limit sell
python cli.py place --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 70000

# Stop-Market sell (bonus order type)
python cli.py place --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.001 --stop-price 60000

# Cancel an order
python cli.py cancel --symbol BTCUSDT --order-id 123456789

# List open orders
python cli.py open-orders --symbol BTCUSDT
"""

from __future__ import annotations

import os
import sys
from typing import Optional

import click
from dotenv import load_dotenv

from bot.client import BinanceFuturesClient, BinanceAPIError
from bot.logging_config import setup_logging
from bot.orders import place_order, print_error

load_dotenv()   # loads .env if present


def _get_client() -> BinanceFuturesClient:
    """Build a client from environment variables, with friendly error messages."""
    api_key = os.getenv("BINANCE_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()

    if not api_key or not api_secret:
        click.echo(
            click.style(
                "\n⚠️  Missing API credentials!\n"
                "   Set BINANCE_API_KEY and BINANCE_API_SECRET in your .env file\n"
                "   or export them as environment variables.\n",
                fg="yellow",
            )
        )
        sys.exit(1)

    return BinanceFuturesClient(api_key=api_key, api_secret=api_secret)


# ── Root group ────────────────────────────────────────────────────────────────

@click.group()
@click.option(
    "--log-level",
    default="INFO",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    help="Logging verbosity (default: INFO).",
    show_default=True,
)
@click.pass_context
def cli(ctx: click.Context, log_level: str) -> None:
    """
    \b
    ╔══════════════════════════════════════════╗
    ║   Binance Futures Testnet Trading Bot    ║
    ╚══════════════════════════════════════════╝

    Trade on Binance USDT-M Futures Testnet from your terminal.
    """
    ctx.ensure_object(dict)
    ctx.obj["logger"] = setup_logging(log_level)


# ── place ─────────────────────────────────────────────────────────────────────

@cli.command("place")
@click.option("--symbol",     required=True,  help="Trading pair, e.g. BTCUSDT")
@click.option(
    "--side",
    required=True,
    type=click.Choice(["BUY", "SELL"], case_sensitive=False),
    help="Order side.",
)
@click.option(
    "--type", "order_type",
    required=True,
    type=click.Choice(["MARKET", "LIMIT", "STOP_MARKET"], case_sensitive=False),
    help="Order type.",
)
@click.option("--quantity",    required=True,  help="Order quantity, e.g. 0.001")
@click.option("--price",       default=None,   help="Limit price (required for LIMIT).")
@click.option("--stop-price",  default=None,   help="Stop price (required for STOP_MARKET).")
@click.option(
    "--tif",
    default="GTC",
    type=click.Choice(["GTC", "IOC", "FOK"], case_sensitive=False),
    help="Time-in-force for LIMIT orders (default: GTC).",
    show_default=True,
)
@click.option(
    "--reduce-only", is_flag=True, default=False,
    help="Mark the order as reduce-only.",
)
@click.pass_context
def place(
    ctx: click.Context,
    symbol: str,
    side: str,
    order_type: str,
    quantity: str,
    price: Optional[str],
    stop_price: Optional[str],
    tif: str,
    reduce_only: bool,
) -> None:
    """Place a new futures order (MARKET / LIMIT / STOP_MARKET)."""
    client = _get_client()
    success = place_order(
        client=client,
        symbol=symbol,
        side=side.upper(),
        order_type=order_type.upper(),
        quantity=quantity,
        price=price,
        stop_price=stop_price,
        time_in_force=tif.upper(),
        reduce_only=reduce_only,
    )
    sys.exit(0 if success else 1)


# ── cancel ────────────────────────────────────────────────────────────────────

@cli.command("cancel")
@click.option("--symbol",   required=True, help="Trading pair, e.g. BTCUSDT")
@click.option("--order-id", required=True, type=int, help="Order ID to cancel.")
@click.pass_context
def cancel(ctx: click.Context, symbol: str, order_id: int) -> None:
    """Cancel an open order by ID."""
    client = _get_client()
    logger = ctx.obj["logger"]
    try:
        resp = client.cancel_order(symbol=symbol.upper(), order_id=order_id)
        click.echo(click.style(f"\n✅  Order {order_id} cancelled successfully.", fg="green"))
        click.echo(f"   Status : {resp.get('status')}")
        logger.info("Cancel response: %s", resp)
    except BinanceAPIError as exc:
        logger.error("Cancel failed: %s", exc)
        print_error(str(exc))
        sys.exit(1)
    except Exception as exc:
        logger.exception("Unexpected error during cancel: %s", exc)
        print_error(f"Unexpected error: {exc}")
        sys.exit(1)


# ── open-orders ───────────────────────────────────────────────────────────────

@cli.command("open-orders")
@click.option("--symbol", default=None, help="Filter by trading pair (optional).")
@click.pass_context
def open_orders(ctx: click.Context, symbol: Optional[str]) -> None:
    """List all open orders (optionally filtered by symbol)."""
    client = _get_client()
    logger = ctx.obj["logger"]
    try:
        orders = client.get_open_orders(symbol=symbol.upper() if symbol else None)
        if not orders:
            click.echo("\n  No open orders found.")
            return
        click.echo(f"\n  {'─'*55}")
        click.echo(f"  Open Orders ({len(orders)} found)")
        click.echo(f"  {'─'*55}")
        for o in orders:
            click.echo(
                f"  [{o.get('orderId')}] {o.get('symbol')} "
                f"{o.get('side')} {o.get('type')} "
                f"qty={o.get('origQty')} price={o.get('price')} "
                f"status={o.get('status')}"
            )
        click.echo(f"  {'─'*55}\n")
    except BinanceAPIError as exc:
        logger.error("Failed to fetch open orders: %s", exc)
        print_error(str(exc))
        sys.exit(1)


# ── ping ─────────────────────────────────────────────────────────────────────

@cli.command("ping")
@click.pass_context
def ping(ctx: click.Context) -> None:
    """Check connectivity to Binance Futures Testnet."""
    client = _get_client()
    logger = ctx.obj["logger"]
    try:
        server_time = client.get_server_time()
        click.echo(
            click.style(
                f"\n  ✅  Connected!  Server time: {server_time} ms\n", fg="green"
            )
        )
        logger.info("Ping successful. Server time: %s", server_time)
    except Exception as exc:
        logger.error("Ping failed: %s", exc)
        print_error(f"Connection failed: {exc}")
        sys.exit(1)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cli(obj={})
