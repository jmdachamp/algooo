# AlgoTrades Scalper Bot V0.2

A Python trading bot that executes the **AlgoTrades Scalper V0.2** Pine Script strategy on a live/paper broker account via TradingView alerts.

```
TradingView Alert → Webhook (FastAPI) → Trade Manager → Alpaca Broker
```

---

## Architecture

| File | Purpose |
|------|---------|
| `main.py` | Entry point – wires broker, trade manager, and webhook server |
| `config.py` | All settings loaded from `.env` |
| `webhook_server.py` | FastAPI server that receives TradingView alert POSTs |
| `trade_manager.py` | Replicates the Pine Script exit logic (partials, breakeven, trailing, max-bars) |
| `broker/base.py` | Abstract broker interface |
| `broker/alpaca_broker.py` | Alpaca Markets implementation |

---

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env with your Alpaca API credentials and strategy params
```

### 3. Run the bot
```bash
python main.py
```

The webhook server starts on `http://0.0.0.0:8000` by default.

---

## TradingView Setup

### Step 1 – Add the Pine Script
Paste the `AlgoTrades Scalper V0.2` Pine Script into a TradingView chart and save it as a strategy.

### Step 2 – Expose your server
Your bot needs a public URL. Options:
- **ngrok** (dev/testing): `ngrok http 8000` → use the `https://xxxx.ngrok.io` URL
- **VPS / cloud server** with a domain (production)

### Step 3 – Create TradingView Alerts

Create **one alert per action** on the strategy. In each alert:

**Alert condition:** select the strategy order you want to capture (e.g. `strategy.entry("LONG", ...)`)

**Webhook URL:** `https://your-server.com/webhook`

**Message body (JSON):**

#### Entry Long
```json
{
  "secret": "YOUR_WEBHOOK_SECRET",
  "action": "LONG",
  "symbol": "{{ticker}}",
  "price": {{close}},
  "comment": "{{strategy.order.comment}}"
}
```

#### Entry Short
```json
{
  "secret": "YOUR_WEBHOOK_SECRET",
  "action": "SHORT",
  "symbol": "{{ticker}}",
  "price": {{close}},
  "comment": "{{strategy.order.comment}}"
}
```

#### Trend Reversal / Close Long
```json
{
  "secret": "YOUR_WEBHOOK_SECRET",
  "action": "CLOSE_LONG",
  "symbol": "{{ticker}}",
  "price": {{close}},
  "comment": "Trend_Reversal"
}
```

#### Trend Reversal / Close Short
```json
{
  "secret": "YOUR_WEBHOOK_SECRET",
  "action": "CLOSE_SHORT",
  "symbol": "{{ticker}}",
  "price": {{close}},
  "comment": "Trend_Reversal"
}
```

> Set `WEBHOOK_SECRET` in your `.env` to match the `"secret"` field in all alert messages.

---

## Strategy Parameters

All strategy parameters mirror the Pine Script inputs and can be tuned in `.env`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `STOP_LOSS_TICKS` | 15 | Stop distance in ticks |
| `TICK_SIZE` | 0.01 | Tick size for your instrument (0.01 stocks, 0.25 ES) |
| `RISK_REWARD` | 2.0 | Final target R:R |
| `ACCOUNT_RISK_PERCENT` | 1.0 | % of equity risked per trade |
| `PARTIAL1_PERCENT` | 50 | % of position closed at first partial |
| `PARTIAL1_RR` | 1.0 | R:R to trigger first partial |
| `BREAKEVEN_RR` | 0.75 | R:R to move stop to breakeven |
| `TRAIL_START_RR` | 1.0 | R:R to start trailing |
| `TRAIL_TICKS` | 10 | Trailing stop distance in ticks |
| `MAX_BARS_OPEN` | 15 | Force-close after N monitor cycles |
| `SESSION_START` | 09:30 | Session open (ET) |
| `SESSION_END` | 15:50 | Session close (ET) |
| `FILTER_LUNCH` | true | Skip 12:15–13:15 ET |
| `PRIME_TIME_ONLY` | false | Only trade prime hours |

---

## Safety Notes

- The bot defaults to **paper trading** (`ALPACA_PAPER=true`). Test thoroughly before going live.
- Set `ALPACA_PAPER=false` only when you are confident in the strategy performance.
- Always use `WEBHOOK_SECRET` to prevent unauthorized order submission.
- Monitor logs in `logs/bot.log` for execution confirmations and errors.

---

## Health Check

```bash
curl http://localhost:8000/health
# {"status":"ok","version":"0.2.0"}
```
