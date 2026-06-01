"""
client.py — Low-level Binance Futures Testnet REST client.

Handles:
  - HMAC-SHA256 request signing
  - Timestamp / recvWindow management
  - HTTP request execution with retries
  - Raw response logging
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger("trading_bot.client")

TESTNET_BASE_URL = "https://testnet.binance.vision"
API_VERSION = "/api/v3"
RECV_WINDOW = 5000          # ms tolerance for clock skew


def _build_session(retries: int = 3) -> requests.Session:
    """Return a requests Session with automatic retry on transient errors."""
    session = requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST", "DELETE"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


class BinanceFuturesClient:
    """
    Thin wrapper around the Binance Futures Testnet REST API.

    Usage
    -----
    client = BinanceFuturesClient(api_key="...", api_secret="...")
    response = client.place_order(symbol="BTCUSDT", side="BUY",
                                   order_type="MARKET", quantity="0.001")
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = TESTNET_BASE_URL,
        timeout: int = 10,
    ) -> None:
        if not api_key or not api_secret:
            raise ValueError("Both api_key and api_secret must be non-empty strings.")
        self._api_key = api_key
        self._api_secret = api_secret
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._session = _build_session()
        self._session.headers.update(
            {
                "X-MBX-APIKEY": self._api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )
        logger.debug("BinanceFuturesClient initialised. Base URL: %s", self._base_url)

    # ── Signing helpers ───────────────────────────────────────────────────────

    def _sign(self, params: Dict[str, Any]) -> str:
        """Return HMAC-SHA256 signature for the given parameter dict."""
        query_string = urlencode(params)
        return hmac.new(
            self._api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _signed_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = RECV_WINDOW
        params["signature"] = self._sign(params)
        return params

    # ── Low-level HTTP methods ────────────────────────────────────────────────

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        url = self._base_url + endpoint
        logger.debug("GET %s  params=%s", url, params)
        resp = self._session.get(url, params=params, timeout=self._timeout)
        return self._handle_response(resp)

    def _post(self, endpoint: str, params: Dict) -> Dict:
        url = self._base_url + endpoint
        signed = self._signed_params(params)
        logger.debug("POST %s  body=%s", url, signed)
        resp = self._session.post(url, data=signed, timeout=self._timeout)
        return self._handle_response(resp)

    def _delete(self, endpoint: str, params: Dict) -> Dict:
        url = self._base_url + endpoint
        signed = self._signed_params(params)
        logger.debug("DELETE %s  params=%s", url, signed)
        resp = self._session.delete(url, params=signed, timeout=self._timeout)
        return self._handle_response(resp)

    @staticmethod
    def _handle_response(resp: requests.Response) -> Dict:
        logger.debug(
            "Response  status=%s  body=%s", resp.status_code, resp.text[:500]
        )
        try:
            data = resp.json()
        except ValueError:
            resp.raise_for_status()
            raise RuntimeError(f"Non-JSON response: {resp.text}")

        if not resp.ok:
            code = data.get("code", resp.status_code)
            msg = data.get("msg", resp.text)
            logger.error("API error  code=%s  msg=%s", code, msg)
            raise BinanceAPIError(code=code, message=msg)

        return data

    # ── Public API methods ────────────────────────────────────────────────────

    def get_server_time(self) -> int:
        """Return Binance server time in milliseconds."""
        data = self._get(f"{API_VERSION}/time")
        return data["serverTime"]

    def get_exchange_info(self) -> Dict:
        return self._get(f"{API_VERSION}/exchangeInfo")

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: str,
        price: Optional[str] = None,
        time_in_force: str = "GTC",
        stop_price: Optional[str] = None,
        reduce_only: bool = False,
    ) -> Dict:
        """
        Place a new futures order.

        Parameters
        ----------
        symbol       : Trading pair, e.g. 'BTCUSDT'
        side         : 'BUY' or 'SELL'
        order_type   : 'MARKET', 'LIMIT', or 'STOP_MARKET'
        quantity     : Order size as a string
        price        : Limit price (required for LIMIT)
        time_in_force: 'GTC' | 'IOC' | 'FOK'  (ignored for MARKET)
        stop_price   : Stop trigger price (required for STOP_MARKET)
        reduce_only  : Whether the order is reduce-only
        """
        params: Dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
        }

        if order_type == "LIMIT":
            if not price:
                raise ValueError("price is required for LIMIT orders.")
            params["price"] = price
            params["timeInForce"] = time_in_force

        elif order_type == "STOP_MARKET":
            if not stop_price:
                raise ValueError("stop_price is required for STOP_MARKET orders.")
            params["stopPrice"] = stop_price

        if reduce_only:
            params["reduceOnly"] = "true"

        logger.info(
            "Placing order  symbol=%s  side=%s  type=%s  qty=%s  price=%s",
            symbol, side, order_type, quantity, price or stop_price or "N/A",
        )
        return self._post(f"{API_VERSION}/order", params)

    def cancel_order(self, symbol: str, order_id: int) -> Dict:
        params = {"symbol": symbol, "orderId": order_id}
        logger.info("Cancelling orderId=%s for %s", order_id, symbol)
        return self._delete(f"{API_VERSION}/order", params)

    def get_open_orders(self, symbol: Optional[str] = None) -> Dict:
        params: Dict[str, Any] = {}
        if symbol:
            params["symbol"] = symbol
        return self._get(f"{API_VERSION}/openOrders", self._signed_params(params))

    def get_account(self) -> Dict:
        return self._get(f"{API_VERSION}/account", self._signed_params({}))


class BinanceAPIError(Exception):
    """Raised when the Binance API returns an error response."""

    def __init__(self, code: Any, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"Binance API Error [{code}]: {message}")
