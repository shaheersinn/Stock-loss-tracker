# Stock Price Alert

A GitHub Actions bot that monitors stock prices every **3 minutes** — including pre-market and post-market hours — and sends Telegram alerts when your target levels are hit.

---

## Tracked Stocks & Thresholds

| Ticker | 🚀 Upside Alerts | 📉 Downside Alerts |
|--------|-----------------|-------------------|
| RKLB   | $95, $99, $105  | $75, $70          |
| ASTS   | $95, $100, $110 | $70               |
| IREN   | $60, $65        | $44               |
| YSS    | $45, $50        | $30, $27          |
| MU     | $550            | $460              |
| RDDT   | $180, $195, $200| $135, $140, $145  |

---

## Schedule

The bot runs every 3 minutes across all extended trading sessions (Mon–Fri):

| Session      | ET              | UTC             |
|--------------|-----------------|-----------------|
| Pre-market   | 04:00 – 09:30   | 09:00 – 14:30   |
| Regular      | 09:30 – 16:00   | 14:30 – 21:00   |
| Post-market  | 16:00 – 20:00   | 21:00 – 01:00   |

> **Note:** GitHub Actions schedules have ~1–2 min jitter and free-tier queuing delays, so exact 3-minute cadence is approximate.

---

## Setup

### 1. Fork / clone this repo

### 2. Add GitHub Secrets

Go to **Settings → Secrets and variables → Actions → New repository secret** and add:

| Secret name        | Value                          |
|--------------------|-------------------------------|
| `TELEGRAM_TOKEN`   | Your Telegram bot token        |
| `TELEGRAM_CHAT_ID` | Your channel or chat ID        |

### 3. Enable Actions

Make sure GitHub Actions is enabled on your repo (it is by default on public repos).

### 4. Test manually

Go to **Actions → Stock Price Alert → Run workflow** to trigger an immediate check.

---

## How it works

- **Price fetching:** Uses `yfinance` which returns pre-market, regular, and post-market prices depending on the current time.
- **Alert deduplication:** `alert_state.json` tracks which levels have fired. An alert fires once when the threshold is crossed, and resets when the price moves back through the level.
- **Telegram messages** include the ticker, price, target, session type (PRE-MARKET / REGULAR / POST-MARKET), and timestamp.

---

## Customizing

Edit the `TARGETS` dict in `alert.py`:

```python
TARGETS = {
    "RKLB": {"up": [95.00, 99.00, 105.00], "down": [75.00, 70.00]},
    # add more tickers here
}
```

`up` and `down` can each be a single number or a list of numbers.
