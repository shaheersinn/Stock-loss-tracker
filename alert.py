import os
import json
import requests
import yfinance as yf
from datetime import datetime, timezone

# ── Target price levels ────────────────────────────────────────────────────────
# Each direction can be a single number or a list of numbers.
TARGETS = {
    "RKLB": {"up": [95.00, 99.00, 105.00], "down": [75.00, 70.00]},
    "ASTS": {"up": [95.00, 100.00, 110.00], "down": [58.00, 60.00,70.00]},
    "IREN": {"up": [60.00, 65.00], "down": [44.00]},
    "YSS":  {"up": [45.00, 50.00], "down": [30.00, 27.00]},
    "MU":   {"up": [550.00], "down": [460.00]},
    "RDDT": {"up": [180.00, 195.00, 200.00], "down": [135.00, 140.00, 145.00]},
}

# ── Telegram config ────────────────────────────────────────────────────────────
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


def get_price_and_session(ticker: str) -> tuple[float | None, str]:
    """
    Returns (price, session_label) where session_label is one of:
    'PRE-MARKET', 'REGULAR', 'POST-MARKET', or 'CLOSED'.
    Uses yfinance fast_info; falls back gracefully.
    """
    try:
        t = yf.Ticker(ticker)
        fi = t.fast_info

        # yfinance exposes pre/post market prices when available
        pre_price  = getattr(fi, "pre_market_price",  None)
        post_price = getattr(fi, "post_market_price", None)
        reg_price  = getattr(fi, "last_price",         None)

        now_utc = datetime.now(timezone.utc)
        hour = now_utc.hour + now_utc.minute / 60  # decimal hour in UTC

        # NYSE/NASDAQ session boundaries (UTC):
        #   Pre-market:  04:00 – 09:30  (08:00–13:30 UTC)  ← using 09:00 UTC as earliest
        #   Regular:     09:30 – 16:00  (13:30–20:00 UTC)
        #   Post-market: 16:00 – 20:00  (20:00–00:00 UTC)
        # We keep it simple: rely on which price field is populated.

        if pre_price and (9.0 <= hour < 13.5):
            return round(float(pre_price), 4), "PRE-MARKET"
        elif post_price and (20.0 <= hour or hour < 1.0):
            return round(float(post_price), 4), "POST-MARKET"
        elif reg_price:
            # During regular hours use regular price; outside hours this is last close.
            if 13.5 <= hour < 20.0:
                return round(float(reg_price), 4), "REGULAR"
            else:
                return round(float(reg_price), 4), "CLOSED (last close)"
        else:
            return None, "UNKNOWN"

    except Exception as e:
        print(f"  ERROR fetching {ticker}: {e}")
        return None, "ERROR"


def normalize_levels(levels) -> list[float]:
    if isinstance(levels, (list, tuple)):
        return sorted({round(float(x), 4) for x in levels})
    return [round(float(levels), 4)]


def check_level(ticker, price, target, direction, session, state, now):
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
            f"🎯 Target price:  `${target:,.2f}`\n"
            f"🕐 Session: `{session}`\n\n"
            f"⏰ {now}"
        )
        send_telegram(msg)
        state[alert_key] = {"fired_at": now, "price_at_fire": price, "session": session}
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

    print(f"\n{'=' * 60}")
    print(f"Stock Alert Check — {now}")
    print(f"{'=' * 60}")

    for ticker, levels in TARGETS.items():
        price, session = get_price_and_session(ticker)
        if price is None:
            print(f"\n  {ticker:6s}  ⚠️  Could not fetch price.")
            continue

        up_levels   = normalize_levels(levels["up"])
        down_levels = normalize_levels(levels["down"])
        up_label    = ", ".join(f"${x:.2f}" for x in up_levels)
        down_label  = ", ".join(f"${x:.2f}" for x in down_levels)

        print(f"\n  {ticker:6s}  price=${price:>10.4f}  [{session}]")
        print(f"          down≤ {down_label}  |  up≥ {up_label}")

        for target in up_levels:
            changed = check_level(ticker, price, target, "up", session, state, now)
            if changed:
                state_changed = True

        for target in down_levels:
            changed = check_level(ticker, price, target, "down", session, state, now)
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
