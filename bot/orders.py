"""
orders.py — High-level order placement logic.

Sits between the CLI layer (cli.py) and the API layer (client.py).
Formats order request summaries and response details for display.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .client import BinanceFuturesClient, BinanceAPIError
from .validators import (
    ValidationError,
    validate_symbol,
    validate_side,
    validate_order_type,
    validate_quantity,
    validate_price,
    validate_stop_price,
)

logger = logging.getLogger("trading_bot.orders")


# ── Pretty-print helpers ──────────────────────────────────────────────────────

def _divider(char: str = "─", width: int = 55) -> str:
    return char * width


def print_request_summary(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str,
    price: Optional[str],
    stop_price: Optional[str],
) -> None:
    print(_divider("═"))
    print("  📋  ORDER REQUEST SUMMARY")
    print(_divider())
    print(f"  Symbol     : {symbol}")
    print(f"  Side       : {side}")
    print(f"  Order Type : {order_type}")
    print(f"  Quantity   : {quantity}")
    if price:
        print(f"  Price      : {price}")
    if stop_price:
        print(f"  Stop Price : {stop_price}")
    print(_divider("═"))


def print_order_response(response: Dict[str, Any]) -> None:
    print(_divider("═"))
    print("  ✅  ORDER PLACED SUCCESSFULLY")
    print(_divider())
    print(f"  Order ID      : {response.get('orderId', 'N/A')}")
    print(f"  Client OID    : {response.get('clientOrderId', 'N/A')}")
    print(f"  Symbol        : {response.get('symbol', 'N/A')}")
    print(f"  Side          : {response.get('side', 'N/A')}")
    print(f"  Type          : {response.get('type', 'N/A')}")
    print(f"  Status        : {response.get('status', 'N/A')}")
    print(f"  Quantity      : {response.get('origQty', 'N/A')}")
    print(f"  Executed Qty  : {response.get('executedQty', 'N/A')}")
    avg_price = response.get("avgPrice") or response.get("price") or "N/A"
    print(f"  Avg Price     : {avg_price}")
    print(f"  Time in Force : {response.get('timeInForce', 'N/A')}")
    print(_divider("═"))


def print_error(message: str) -> None:
    print(_divider("═"))
    print("  ❌  ORDER FAILED")
    print(_divider())
    print(f"  Reason : {message}")
    print(_divider("═"))


# ── Core order function ───────────────────────────────────────────────────────

def place_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: str,
    price: Optional[str] = None,
    stop_price: Optional[str] = None,
    time_in_force: str = "GTC",
    reduce_only: bool = False,
) -> bool:
    """
    Validate inputs, print request summary, call the API, and print the result.

    Returns True on success, False on failure.
    """

    # ── Validate ──────────────────────────────────────────────────────────────
    try:
        symbol = validate_symbol(symbol)
        side = validate_side(side)
        order_type = validate_order_type(order_type)
        quantity = validate_quantity(quantity)
        price = validate_price(price, order_type)
        stop_price = validate_stop_price(stop_price)
    except ValidationError as exc:
        logger.warning("Validation failed: %s", exc)
        print_error(str(exc))
        return False

    # ── Print summary ─────────────────────────────────────────────────────────
    print_request_summary(symbol, side, order_type, quantity, price, stop_price)
    logger.info(
        "Validated order request  symbol=%s side=%s type=%s qty=%s price=%s",
        symbol, side, order_type, quantity, price or stop_price or "N/A",
    )

    # ── Place order ───────────────────────────────────────────────────────────
    try:
        response = client.place_order(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            time_in_force=time_in_force,
            reduce_only=reduce_only,
        )
    except BinanceAPIError as exc:
        logger.error("API error while placing order: %s", exc)
        print_error(str(exc))
        return False
    except Exception as exc:
        logger.exception("Unexpected error while placing order: %s", exc)
        print_error(f"Unexpected error: {exc}")
        return False

    # ── Print result ──────────────────────────────────────────────────────────
    logger.info("Order placed successfully. Response: %s", response)
    print_order_response(response)
    return True
