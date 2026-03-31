import os
import json
import requests
import yfinance as yf
from datetime import datetime, timezone

# ── Target price levels ────────────────────────────────────────────────────────
# Each direction can be either:
#   - a single number (backward compatible), or
#   - a list of numbers for multiple alert levels.
TARGETS = {
    "INTC": {"up": [48.00, 50.00,54.00], "down": 43.00},
    "AMD": {"up": [220.00, 240.00, 260.00], "down": [199.00, 180.00, 160.00]},
    "RKLB": {"up": [90.00,75.00,85.00], "down": 67.00},
    "APLD": {"up": [40.00, 30.00, 29.00], "down": 25.00},
    "POET": {"up": [10.00,8.00], "down":  6.00},
    "ONDS": {"up": 15.00, "down": 8.00},
    "NVDA": {"up": [190.00, 196.00,205.00], "down": 178.00},
    "MU": {"up": 480.00, "down": [305.00, 410.00, 420.00, 430.00,440.00]},
}

# ── Telegram config ────────────────────────────────────────────────────────────
# Accepts either TELEGRAM_TOKEN or TELEGRAM_BOT_TOKEN as the secret name
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not TELEGRAM_TOKEN:
    raise RuntimeError(
        "Neither TELEGRAM_TOKEN nor TELEGRAM_BOT_TOKEN secret is set. "
        "Go to repo Settings > Secrets > Actions and add one."
    )
if not TELEGRAM_CHAT_ID:
    raise RuntimeError("TELEGRAM_CHAT_ID secret is not set.")

# ── Alert state file ───────────────────────────────────────────────────────────
STATE_FILE = "alert_state.json"


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
    }
    r = requests.post(url, json=payload, timeout=10)
    r.raise_for_status()
    print("  ✅ Telegram alert sent.")


def get_price(ticker: str) -> float | None:
    try:
        data = yf.Ticker(ticker)
        price = data.fast_info["last_price"]
        return round(float(price), 4)
    except Exception as e:
        print(f"  ERROR fetching {ticker}: {e}")
        return None


def normalize_levels(levels) -> list[float]:
    if isinstance(levels, (list, tuple)):
        return sorted({round(float(x), 4) for x in levels})
    return [round(float(levels), 4)]


def check_level(ticker, price, target, direction, state, now):
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
        send_telegram(msg)
        state[alert_key] = {"fired_at": now, "price_at_fire": price}
        return True

    if not hit and state.get(alert_key):
        print(f"    {direction.upper()} alert for {ticker} @ ${target} reset (price moved away).")
        del state[alert_key]
        return True

    return False


def main():
    state = load_state()
    state_changed = False
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    print(f"\n{'=' * 55}")
    print(f"Stock Alert Check — {now}")
    print(f"{'=' * 55}")

    for ticker, levels in TARGETS.items():
        price = get_price(ticker)
        if price is None:
            continue

        up_levels = normalize_levels(levels["up"])
        down_levels = normalize_levels(levels["down"])
        up_label = ", ".join(f"${x:.2f}" for x in up_levels)
        down_label = ", ".join(f"${x:.2f}" for x in down_levels)

        print(f"\n  {ticker:6s}  price=${price:>10.4f}  [down≤ {down_label} | up≥ {up_label}]")

        for target in up_levels:
            changed = check_level(ticker, price, target, "up", state, now)
            if changed:
                state_changed = True

        for target in down_levels:
            changed = check_level(ticker, price, target, "down", state, now)
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
