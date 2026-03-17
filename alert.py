import os
import json
import requests
import yfinance as yf
from datetime import datetime, timezone

# ── Target price levels ────────────────────────────────────────────────────────
# Each entry: {"up": <price>, "down": <price>}
# Alert fires when price >= up  OR  price <= down
TARGETS = {
    "INTC": {"up": 54.00,  "down": 40.00},
    "AMD":  {"up": 260.00, "down": 199.00},
    "RKLB": {"up": 90.00,  "down": 50.00},
    "APLD": {"up": 40.00,  "down": 24.00},
    "POET": {"up": 10.00,  "down": 5.00},
    "ONDS": {"up": 16.00,  "down": 8.00},
    "NVDA": {"up": 211.00, "down": 178.00},
    "MU":   {"up": 480.00, "down": 415.00},
}

# ── Telegram config (set as GitHub Secrets) ────────────────────────────────────
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

# ── Alert state file (committed to repo to persist across runs) ────────────────
STATE_FILE = "alert_state.json"


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def send_telegram(message: str) -> bool:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("  ⚠️ Telegram credentials are missing. Skipping alert send.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"  ⚠️ Telegram alert failed: {e}")
        return False

    print("  ✅ Telegram alert sent.")
    return True


def get_price(ticker: str) -> float | None:
    try:
        data = yf.Ticker(ticker)
        price = data.fast_info["last_price"]
        return round(float(price), 4)
    except Exception as e:
        print(f"  ERROR fetching {ticker}: {e}")
        return None


def check_level(ticker, price, target, direction, state, now):
    """Check one price level and fire a Telegram alert if needed.
    Returns True if state was changed."""
    alert_key = f"{ticker}_{direction}_{target}"

    if direction == "up":
        hit = price >= target
        emoji = "🚀"
        label = "UPSIDE TARGET HIT"
        detail = f"price has risen to or above `${target:,.2f}`"
    else:
        hit = price <= target
        emoji = "📉"
        label = "DOWNSIDE TARGET HIT"
        detail = f"price has fallen to or below `${target:,.2f}`"

    if hit and not state.get(alert_key):
        msg = (
            f"{emoji} *{label}*\n\n"
            f"*{ticker}* — {detail}\n\n"
            f"💰 Current price: `${price:,.4f}`\n"
            f"🎯 Target price:  `${target:,.2f}`\n\n"
            f"⏰ {now}"
        )
        if send_telegram(msg):
            state[alert_key] = {"fired_at": now, "price_at_fire": price}
            return True
        print(f"  ⚠️ Alert condition hit for {ticker} but delivery failed; will retry next run.")
        return False

    elif not hit and state.get(alert_key):
        # Price moved back through the level — reset so it can fire again later
        print(f"    {direction.upper()} alert for {ticker} @ ${target} reset (price moved away).")
        del state[alert_key]
        return True

    return False


def main():
    state = load_state()
    state_changed = False
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    print(f"\n{'='*55}")
    print(f"Stock Alert Check — {now}")
    print(f"{'='*55}")

    for ticker, levels in TARGETS.items():
        price = get_price(ticker)
        if price is None:
            continue

        print(f"\n  {ticker:6s}  price=${price:>10.4f}  "
              f"[down≤${levels['down']:.2f} | up≥${levels['up']:.2f}]")

        for direction, target in [("up", levels["up"]), ("down", levels["down"])]:
            changed = check_level(ticker, price, target, direction, state, now)
            if changed:
                state_changed = True

    print()
    if state_changed:
        save_state(state)
        print("State file updated.")
    else:
        print("No state changes.")


if __name__ == "__main__":
    main()
