import numpy as np
import pandas as pd

from toss_quant.backtest import Params, add_signals, backtest


def make(closes, opens=None):
    n = len(closes)
    c = np.array(closes, float)
    o = np.array(opens, float) if opens is not None else c.copy()
    return pd.DataFrame({"date": pd.date_range("2022-01-03", periods=n, freq="B"),
                         "open": o, "high": np.maximum(o, c) * 1.005, "low": np.minimum(o, c) * 0.995,
                         "close": c, "volume": 1.0})


def wave(n=700):
    x = np.arange(n)
    return 100 + 0.05 * x + 25 * np.sin(x / 40)


def test_golden_cross_entry_uses_next_open_and_dead_cross_exit():
    df = make(wave())
    P = Params(buy_cost=0, sell_cost=0)
    sig = add_signals(df, P)
    r = backtest(df, P)
    assert r["n_trades"] >= 2
    t = r["trades"][0]
    # 체결가는 신호 다음 날 시가여야 한다 (미래 참조 금지)
    i = df.index[df.date == t["entry_date"]][0]
    assert sig.entry.iloc[i - 1] and t["entry_price"] == df.open.iloc[i]
    first_closed = next(x for x in r["trades"] if x["exit_date"] is not None)
    j = df.index[df.date == first_closed["exit_date"]][0]
    assert first_closed["exit_price"] == df.open.iloc[j]  # 청산도 신호 다음 날 시가
    assert first_closed["exit_reason"] in ("데드크로스", "60일선 이탈 5일")


def test_exit_after_five_days_below_ma60():
    # 상승 후 급락 → 60일선 아래 5일 연속이면 청산 (데드크로스보다 먼저)
    flat = list(np.linspace(130, 100, 230))       # 워밍업 구간(신호 무시) 이후에 골든크로스가 나오도록
    up = list(np.linspace(100, 200, 100))
    crash = [150] * 120
    df = make(flat + up + crash)
    r = backtest(df, Params(buy_cost=0, sell_cost=0))
    assert r["n_trades"] == 1 and r["trades"][0]["reason"] == "골든크로스"
    assert r["trades"][0]["exit_date"] is not None


def test_costs_reduce_return_and_no_crash_on_short_data():
    df = make(wave())
    free = backtest(df, Params(buy_cost=0, sell_cost=0))["strategy"]["total_return"]
    paid = backtest(df, Params(buy_cost=0.01, sell_cost=0.01))["strategy"]["total_return"]
    assert paid < free
    try:
        backtest(make([100] * 50))
    except ValueError as e:
        assert "데이터가 부족" in str(e)
    else:
        raise AssertionError


def test_pullback_signal_fires_only_in_uptrend():
    x = np.arange(600)
    x = np.arange(900)
    up = make(100 + 0.12 * x + 22 * np.sin(x / 35))   # 200일선이 오르는 가운데 가격이 200일선을 오르내림
    sig = add_signals(up, Params())
    assert sig.pullback.sum() >= 1
    flat_down = make(300 - 0.12 * x + 22 * np.sin(x / 35))
    assert add_signals(flat_down, Params()).pullback.sum() == 0
