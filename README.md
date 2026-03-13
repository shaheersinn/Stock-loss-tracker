# 📈 Stock Price Alert Bot

Sends a **Telegram alert** the moment a watched stock hits its target price.
Runs automatically every **15 minutes** during US market hours via GitHub Actions — no server required.

---

## 🎯 Watched Targets

| Ticker | 📉 Downside Alert | 🚀 Upside Alert |
|--------|------------------|----------------|
| INTC   | ≤ $40.00         | ≥ $54.00       |
| AMD    | ≤ $180.00        | ≥ $260.00      |
| RKLB   | ≤ $50.00         | ≥ $90.00       |
| APLD   | ≤ $20.00         | ≥ $40.00       |
| POET   | ≤ $3.00          | ≥ $11.00       |
| ONDS   | ≤ $6.00          | ≥ $16.00       |
| NVDA   | ≤ $170.00        | ≥ $211.00      |
| MU     | ≤ $360.00        | ≥ $480.00      |

---

## 🚀 Setup (one-time, ~5 minutes)

### 1 — Fork / clone this repo
```bash
git clone https://github.com/YOUR_USERNAME/stock-alerts.git
cd stock-alerts
```

### 2 — Create a Telegram Bot

1. Open Telegram and message **@BotFather**
2. Send `/newbot`, follow the prompts
3. Copy the **API token** it gives you (looks like `123456:ABC-DEF...`)

### 3 — Get your Telegram Chat ID

1. Message your new bot anything (e.g. "hi")
2. Open this URL in your browser (replace `YOUR_TOKEN`):
   ```
   https://api.telegram.org/botYOUR_TOKEN/getUpdates
   ```
3. Find `"chat":{"id": 123456789}` — that number is your **Chat ID**

### 4 — Add GitHub Secrets

Go to your repo → **Settings → Secrets and variables → Actions → New repository secret**

| Secret name        | Value                        |
|--------------------|------------------------------|
| `TELEGRAM_TOKEN`   | Your bot API token           |
| `TELEGRAM_CHAT_ID` | Your chat ID (the number)    |

### 5 — Enable Actions

Go to the **Actions** tab in your repo and click **"I understand my workflows, enable them"** if prompted.

That's it! ✅ The workflow will now run automatically.

---

## ⚙️ How it works

- GitHub Actions runs the script every **15 minutes**, Monday–Friday, during US market hours (9:30 AM – 5:00 PM ET).
- `yfinance` fetches the latest price for each ticker.
- If a stock's price **≥ its target**, a Telegram message is sent.
- The alert state is saved in `alert_state.json` (committed back to the repo), so you **won't receive duplicate alerts** while the stock stays above target.
- If the price **drops back below** the target, the alert resets — so you'll get notified again if it bounces back up.

---

## 🔧 Customising targets

Edit `alert.py` and modify the `TARGETS` dict:

```python
TARGETS = {
    "INTC":  54.00,
    "AMD":  260.00,
    # add / change / remove as needed
}
```

Commit and push — the next scheduled run will pick up the changes.

---

## 🧪 Manual test run

Trigger a run instantly from the **Actions** tab → **Stock Price Alert** → **Run workflow**.
