# Binance Futures Testnet Trading Bot

A clean, well-structured Python CLI application for placing orders on the **Binance USDT-M Futures Testnet**.

---

## Features

| Feature | Detail |
|---|---|
| Order types | `MARKET`, `LIMIT`, `STOP_MARKET` (bonus) |
| Sides | `BUY` / `SELL` |
| CLI | Built with [Click](https://click.palletsprojects.com/) — argparse-compatible |
| Logging | Structured logs to console + rotating file (`logs/trading_bot.log`) |
| Error handling | Validation errors, API errors, network failures — all caught and displayed cleanly |
| Code structure | Separate `client.py`, `orders.py`, `validators.py`, `logging_config.py`, `cli.py` |

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py
│   ├── client.py          # Binance REST API wrapper (signing, retries, HTTP)
│   ├── orders.py          # Order placement logic + pretty-print helpers
│   ├── validators.py      # Input validation (symbol, side, qty, price, etc.)
│   └── logging_config.py  # Console + rotating file logger setup
├── cli.py                 # CLI entry point (Click commands)
├── logs/
│   └── trading_bot.log    # Auto-created on first run
├── .env.example           # Rename to .env and add your keys
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Get Testnet API Credentials

1. Visit [https://testnet.binancefuture.com](https://testnet.binancefuture.com)
2. Log in (or register with a GitHub account)
3. Go to **API Management** → Generate a new API key
4. Copy the **API Key** and **Secret Key**

### 2. Clone / Download the Project

```bash
git clone https://github.com/your-username/trading_bot.git
cd trading_bot
```

### 3. Create a Virtual Environment

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Credentials

```bash
cp .env.example .env
```

Open `.env` and fill in your keys:

```env
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_api_secret_here
```

> ⚠️ Never commit your `.env` file — it is already in `.gitignore`.

---

## How to Run

All commands are run from the project root:

```bash
python cli.py [COMMAND] [OPTIONS]
```

### Check Connectivity

```bash
python cli.py ping
```

---

### Place a MARKET Order

```bash
# Buy 0.001 BTC at market price
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

# Sell 0.01 ETH at market price
python cli.py place --symbol ETHUSDT --side SELL --type MARKET --quantity 0.01
```

**Sample output:**
```
═══════════════════════════════════════════════════════
  📋  ORDER REQUEST SUMMARY
───────────────────────────────────────────────────────
  Symbol     : BTCUSDT
  Side       : BUY
  Order Type : MARKET
  Quantity   : 0.001
═══════════════════════════════════════════════════════
═══════════════════════════════════════════════════════
  ✅  ORDER PLACED SUCCESSFULLY
───────────────────────────────────────────────────────
  Order ID      : 4751823901
  Symbol        : BTCUSDT
  Side          : BUY
  Type          : MARKET
  Status        : FILLED
  Quantity      : 0.001
  Executed Qty  : 0.001
  Avg Price     : 67254.30
═══════════════════════════════════════════════════════
```

---

### Place a LIMIT Order

```bash
# Sell 0.001 BTC with a limit price of 70000
python cli.py place --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 70000

# Buy 0.01 ETH with a limit price of 3200, IOC time-in-force
python cli.py place --symbol ETHUSDT --side BUY --type LIMIT --quantity 0.01 --price 3200 --tif IOC
```

---

### Place a STOP_MARKET Order (Bonus Order Type)

```bash
# Stop-market sell triggered at 60000
python cli.py place --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.001 --stop-price 60000
```

---

### Cancel an Open Order

```bash
python cli.py cancel --symbol BTCUSDT --order-id 4751829042
```

---

### List Open Orders

```bash
# All open orders
python cli.py open-orders

# Filter by symbol
python cli.py open-orders --symbol BTCUSDT
```

---

### Adjust Log Verbosity

```bash
# Show DEBUG logs in console (very verbose)
python cli.py --log-level DEBUG place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

---

## Logging

Logs are written to **`logs/trading_bot.log`** automatically.

- Console: `INFO` and above
- File: `DEBUG` and above (full request/response details)
- File rotates at 5 MB, keeping 3 backups

Sample log entries are provided in `logs/trading_bot.log`.

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Missing API keys | Friendly message + exit 1 |
| Invalid symbol / side / type | Validation error shown before API call |
| Missing price for LIMIT | Validation error |
| API error (e.g. `-1121 Invalid symbol`) | Formatted error with Binance code + message |
| Network timeout / retry exhausted | Exception caught, error displayed |
| Unexpected exception | Caught, logged with full traceback in file |

---

## Assumptions

- The bot targets the **USDT-M Futures Testnet** only (`https://testnet.binancefuture.com`).
- `quantity` precision depends on the symbol's lot size filter; the testnet is lenient but production would require rounding.
- `STOP_MARKET` is included as the bonus third order type.
- Credentials are loaded from a `.env` file or environment variables — never hardcoded.
- `timeInForce` defaults to `GTC` for LIMIT orders; can be overridden with `--tif`.

---

## Dependencies

```
requests>=2.31.0       # HTTP client with retry support
click>=8.1.7           # CLI framework
python-dotenv>=1.0.0   # .env file loading
urllib3>=2.0.0         # Used by requests for retries
```

---

## Running Tests (optional)

```bash
# Quick smoke test — just check the ping
python cli.py ping

# Place a tiny market order
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```
