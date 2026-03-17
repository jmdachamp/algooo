# algooo — TradingView Algo Bot

Automated trading bot for futures (NQ, GC, RTY, YM) driven by TradingView
indicator alerts. Supports **Tradovate** and **Interactive Brokers**.

## How it works

```
TradingView indicator fires alert
        │
        ▼  (JSON via webhook)
FastAPI webhook server  ──►  TradeManager  ──►  Broker API
                                                (Tradovate / IBKR)
                                │
                                ▼
                    Market entry order
                    + Native trailing stop order
```

1. You set a TradingView alert on your indicator's green arrow condition.
2. TradingView POSTs a JSON payload to your bot's webhook URL.
3. The bot places a market entry and immediately attaches a native trailing
   stop on the broker side.
4. If your indicator also fires exit signals you can send `"action": "exit"`.

---

## Quick start

### 1. Install dependencies

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure credentials

```bash
cp .env.example .env
# Edit .env with your Tradovate or IBKR credentials
```

### 3. Edit config.yaml

Adjust per-instrument settings:

```yaml
broker: tradovate        # or: ibkr
paper_trading: true      # ALWAYS test on paper first

webhook:
  secret_token: "my-secret-123"   # pick any random string

instruments:
  NQ:
    quantity: 1
    trail_points: 20     # 20 NQ points = $400 max trail
```

### 4. Run the bot

```bash
python -m bot.webhook_server
```

The server starts on `http://0.0.0.0:8000`.

---

## TradingView alert setup

1. Open your chart and right-click the indicator → **Add alert**
2. Set the condition to the green arrow signal
3. In **Alert actions → Webhook URL**, enter:
   ```
   http://YOUR_SERVER_IP:8000/webhook?token=YOUR_SECRET_TOKEN
   ```
4. In the **Message** box, paste this JSON:
   ```json
   {
     "symbol": "{{ticker}}",
     "action": "buy",
     "price": {{close}}
   }
   ```
   - For short signals: `"action": "sell"`
   - For exit signals: `"action": "exit"`

> **Tip:** If your server is on your local machine, use a tunneling tool like
> [ngrok](https://ngrok.com) so TradingView can reach it:
> `ngrok http 8000`

---

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/webhook?token=…` | Receive TradingView alert |
| GET | `/status` | Health check + open trades + balance |

### Example webhook payload

```json
{
  "symbol": "NQ",
  "action": "buy",
  "price": 19250.75
}
```

### Example status response

```json
{
  "status": "running",
  "broker": "tradovate",
  "paper_trading": true,
  "open_trades": {
    "NQ": {
      "side": "buy",
      "quantity": 1,
      "entry_price": 19250.75,
      "opened_at": "2025-01-15T14:32:00",
      "trail_order_id": "98765"
    }
  },
  "account_balance": 50000.0
}
```

---

## Broker setup

### Tradovate

1. Create a developer app at https://trader.tradovate.com → Settings → API
2. Note your **CID** and **Secret**
3. Fill in `.env` with your username, password, CID, and secret

### Interactive Brokers

1. Install [TWS](https://www.interactivebrokers.com/en/trading/tws.php) or
   [IB Gateway](https://www.interactivebrokers.com/en/trading/ibgateway.php)
2. Enable API access: Edit → Global Configuration → API → Settings
   - Enable ActiveX and Socket Clients
   - Set Socket port (default 7497 paper / 7496 live)
3. Uncomment `ib_insync` in `requirements.txt` and reinstall
4. Set `broker: ibkr` in `config.yaml`

---

## File structure

```
algooo/
├── bot/
│   ├── webhook_server.py   # FastAPI app + entry point
│   ├── trade_manager.py    # Entry/exit/trail logic
│   ├── config.py           # Config loader
│   └── brokers/
│       ├── base.py         # Abstract interface
│       ├── tradovate.py    # Tradovate REST adapter
│       └── ibkr.py         # IBKR ib_insync adapter
├── config.yaml             # Your settings
├── .env                    # Your credentials (never commit)
├── .env.example            # Template
└── requirements.txt
```

---

## Safety notes

- Always start with `paper_trading: true` and verify fills in your broker's
  paper account before going live.
- The bot trades **one position per symbol** at a time — duplicate signals
  are silently ignored.
- Set `max_loss_usd` per instrument in `config.yaml` as a reference (logged
  but not enforced by a hard order — add your own risk layer if needed).
- Keep your `.env` file private — it contains account credentials.
