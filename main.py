"""Deep-Value Sniper: a cbBTC/USDC bot for agent-fun/bars-replay/v1.

Profile: few trades, tiny drawdown. The bot sits in cash and only buys a
deep dislocation below the short mean once selling looks exhausted, then
sells into the recovery. Every round trip costs roughly 26 bps in fees,
slippage and impact, so entries demand a dip far larger than that.

Rules (all decisions on a bar's close, fills at the next bar's open):
  - Mean: mean of the last 60 closes. Trend guard: EMA of the last 240
    closes, kept as a streaming EMA (step 2/(240+1) toward each new close,
    initialised at the first close seen, so the guard is live from the
    start of the window and converges to the 240-bar EMA).
  - BUY, only when flat: close <= mean60 * (1 - DIP_BPS) and the minimum
    close of the last 3 bars is >= the minimum close of the 3 bars before
    them (stabilization: sellers are exhausting) and close >= EMA240 *
    (1 - 300 bps) (a dip, not a total collapse). Size: 100% of cash.
  - SELL, only when holding: close >= mean60 (target reached), or a
    trailing stop (once the gain reaches +80 bps, sell if the close falls
    40 bps below the highest close since entry), or a hard stop at
    -100 bps from entry cost, or the position has been held 240 bars.

Deterministic: no clock, no randomness, float arithmetic on the closes
only. Python 3.13 standard library only; the wire protocol is spoken by
the vendored byte-identical SDK shim under vendor/.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))

import makefun_bars

SYMBOL = "CBBTC"

# --- Strategy parameters (basis points unless noted) ---
MEAN_N = 60            # bars in the short mean the dip is measured against
EMA_N = 240            # bars in the trend-guard EMA
DIP_BPS = 100          # buy only this far below mean60 (tuned: best of 100/120/150 on the dev grade)
COLLAPSE_BPS = 300     # never buy further than this below EMA240
TRAIL_ARM_BPS = 80     # trailing stop arms once the gain reaches this
TRAIL_GIVE_BPS = 40    # ...and fires this far below the highest close
HARD_STOP_BPS = 100    # sell at once this far under entry cost
MAX_HOLD_BARS = 240    # sell after this many bars in the position
MAX_SLIPPAGE_BPS = 150  # per instructions: fills are not rejected on noise

BPS = 10_000

# --- Rolling indicator state (this bot trades one symbol) ---
_closes = []           # every CBBTC close seen, oldest first (ints)
_ema240 = None         # streaming EMA240, initialised at the first close


def _push_close(close):
    """Fold one new close into the rolling mean window and the EMA240."""
    global _ema240
    _closes.append(close)
    if _ema240 is None:
        _ema240 = float(close)
    else:
        _ema240 += (2.0 / (EMA_N + 1)) * (close - _ema240)


def _mean60():
    """Mean of the last MEAN_N closes, or None until enough bars exist."""
    if len(_closes) < MEAN_N:
        return None
    return sum(_closes[-MEAN_N:]) / MEAN_N


def _stabilized():
    """True when selling looks exhausted: the lowest close of the last
    3 bars no longer undercuts the lowest close of the 3 bars before."""
    if len(_closes) < 6:
        return False
    return min(_closes[-3:]) >= min(_closes[-6:-3])


# --- Position tracking (derived each batch from the account) ---
_bars_held = 0         # batches seen since the position first appeared
_high_since_entry = None  # highest close since entry (ints, price units)


def _sell_order(state, held):
    return {
        "side": "sell",
        "symbol": SYMBOL,
        "qty": held.qty,
        "max_slippage_bps": MAX_SLIPPAGE_BPS,
    }


def _exit_reason(state, held, close, mean60):
    """Why a held position should be sold on this close, or None."""
    if mean60 is not None and close >= mean60:
        return "target"
    value = state.value(SYMBOL, held.qty)
    if held.cost > 0:
        gain_bps = (value - held.cost) * BPS // held.cost
        if gain_bps <= -HARD_STOP_BPS:
            return "hard_stop"
        if (
            gain_bps >= TRAIL_ARM_BPS
            and _high_since_entry is not None
            and close * BPS <= _high_since_entry * (BPS - TRAIL_GIVE_BPS)
        ):
            return "trailing_stop"
    if _bars_held >= MAX_HOLD_BARS:
        return "max_hold"
    return None


def on_batch(state, batch):
    global _bars_held, _high_since_entry

    # Fold this batch's CBBTC bar (if any) into the indicators first:
    # decisions are made on the close of the bar that just closed.
    fresh_close = None
    for bar in batch["bars"]:
        if bar["symbol"] == SYMBOL:
            fresh_close = int(bar["c"])
            _push_close(fresh_close)
    if fresh_close is None or state.warming_up:
        return []

    held = state.positions.get(SYMBOL)
    if held is not None:
        _bars_held += 1
        if _high_since_entry is None or fresh_close > _high_since_entry:
            _high_since_entry = fresh_close
        if _exit_reason(state, held, fresh_close, _mean60()) is not None:
            return [_sell_order(state, held)]
        return []

    # Flat: reset the per-entry trackers, then look for a deep dip.
    _bars_held = 0
    _high_since_entry = None
    mean60 = _mean60()
    if mean60 is None or _ema240 is None:
        return []
    if fresh_close * BPS > mean60 * (BPS - DIP_BPS):
        return []  # not deep enough below the mean
    if not _stabilized():
        return []  # sellers not exhausted yet
    if fresh_close * BPS < _ema240 * (BPS - COLLAPSE_BPS):
        return []  # a collapse, not a dip: stay out

    size = state.cash
    room = state.weight_room(SYMBOL)
    if 0 < room < size:
        size = room
    min_notional = int(state.hello["fees"]["min_notional_quote_units"])
    if size < min_notional:
        return []
    return [
        {
            "side": "buy",
            "symbol": SYMBOL,
            "notional_quote_units": size,
            "max_slippage_bps": MAX_SLIPPAGE_BPS,
        }
    ]


if __name__ == "__main__":
    makefun_bars.run(on_batch)
