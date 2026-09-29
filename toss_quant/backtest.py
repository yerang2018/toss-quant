"""20-60 골든크로스 + 200일선 눌림목 전략 백테스트 (종목별 독립, 롱 온리, 전액 투자).

규칙(모든 신호는 '종가' 확정 후 판단하고, 체결은 '다음 거래일 시가' — 미래 참조 방지)
  진입 ① 20일선이 60일선을 상향 돌파(골든크로스)
       ② 200일선 상승 중(200일선 > 20거래일 전 값) AND 직전 5거래일 종가가 모두 200일선 위
          AND 직전일 종가가 6거래일 전보다 낮음(하락 중) AND 당일 저가가 200일선에 닿고 종가는 200일선 이상(지지)
  청산 ① 보유 후 종가가 60일선 아래인 날이 연속 5거래일 (이탈일 포함)
       ② 20일선이 60일선을 하향 돌파(데드크로스)
200일선 계산을 위해 앞 200거래일은 신호 없이 워밍업으로만 사용한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class Params:
    fast: int = 20
    slow: int = 60
    trend: int = 200
    slope_lookback: int = 20      # 200일선 상승 판단 기간
    above_days: int = 5           # 눌림 전 200일선 위에 머문 최소 일수
    decline_lookback: int = 5     # '하락하다가' 판단 기간
    recover_days: int = 5         # 60일선 이탈 후 회복 못하면 청산하는 연속 일수
    buy_cost: float = 0.0015      # 매수 수수료+슬리피지(편도)
    sell_cost: float = 0.0035     # 매도 수수료+세금+슬리피지
    warmup: int = 200


def market_costs(currency: str) -> dict:
    """기본값(가정): 국내 수수료 0.015%+매도세 0.20%+슬리피지 0.05% / 미국 수수료 0.10%+슬리피지 0.05%."""
    if currency == "KRW":
        return {"buy_cost": 0.00065, "sell_cost": 0.00265}
    return {"buy_cost": 0.0015, "sell_cost": 0.0015}


def add_signals(df: pd.DataFrame, p: Params) -> pd.DataFrame:
    d = df.copy()
    c = d["close"]
    d["ma_f"], d["ma_s"], d["ma_t"] = (c.rolling(n).mean() for n in (p.fast, p.slow, p.trend))
    d["golden"] = (d.ma_f > d.ma_s) & (d.ma_f.shift(1) <= d.ma_s.shift(1))
    d["dead"] = (d.ma_f < d.ma_s) & (d.ma_f.shift(1) >= d.ma_s.shift(1))
    above = (c > d.ma_t).astype(float)
    was_above = above.shift(1).rolling(p.above_days).min() == 1
    rising = d.ma_t > d.ma_t.shift(p.slope_lookback)
    falling = c.shift(1) < c.shift(1 + p.decline_lookback)
    touch = (d.low <= d.ma_t) & (d.close >= d.ma_t)
    d["pullback"] = rising & was_above & falling & touch
    d["entry"] = d.golden | d.pullback
    return d


def backtest(df: pd.DataFrame, p: Params | None = None) -> dict:
    p = p or Params()
    d = add_signals(df, p)
    n = len(d)
    if n <= p.warmup + 2:
        raise ValueError(f"데이터가 부족합니다({n}봉). 최소 {p.warmup + 3}봉이 필요합니다.")
    o, c, ma_s = d.open.values, d.close.values, d.ma_s.values
    entry, dead = d.entry.values, d.dead.values
    golden = d.golden.values

    cash, units, equity, invested = 1.0, 0.0, np.full(n, np.nan), np.zeros(n, dtype=bool)
    trades, cur, below = [], None, 0
    for i in range(p.warmup, n):
        # 어제 종가 기준 신호를 오늘 시가에 체결
        if i > p.warmup:
            j = i - 1
            if units == 0 and entry[j]:
                units = cash * (1 - p.buy_cost) / o[i]
                cur = {"entry_date": d.date[i], "entry_price": o[i],
                       "reason": "골든크로스" if golden[j] else "200일선 눌림", "cash_in": cash}
                cash, below = 0.0, 0
            elif units > 0 and (below >= p.recover_days or dead[j]):
                cash = units * o[i] * (1 - p.sell_cost)
                cur.update(exit_date=d.date[i], exit_price=o[i], ret=cash / cur["cash_in"] - 1,
                           exit_reason="데드크로스" if dead[j] else f"60일선 이탈 {p.recover_days}일",
                           days=int((d.date[i] - cur["entry_date"]).days))
                trades.append(cur)
                units, cur = 0.0, None
        # 종가 기준 상태 갱신
        if units > 0:
            below = below + 1 if c[i] < ma_s[i] else 0
        invested[i] = units > 0
        equity[i] = cash + units * c[i]

    if cur is not None:  # 미청산 포지션은 마지막 종가로 평가(미실현)
        cur.update(exit_date=None, exit_price=c[-1], ret=equity[-1] / cur["cash_in"] - 1,
                   exit_reason="보유 중(미실현)", days=int((d.date.iloc[-1] - cur["entry_date"]).days))
        trades.append(cur)

    # 비교 기준: 워밍업 직후 첫 시가에 매수해 계속 보유(같은 비용 적용)
    idx = d.date[p.warmup + 1:]
    eq = pd.Series(equity[p.warmup + 1:], index=idx)
    bh = pd.Series(c[p.warmup + 1:] / o[p.warmup + 1], index=idx) * (1 - p.buy_cost)
    years = max((idx.iloc[-1] - idx.iloc[0]).days / 365.25, 1e-9)

    def stats(s: pd.Series) -> dict:
        base = 1.0 if s is bh else equity[p.warmup]  # 전략은 1.0에서 시작
        total = s.iloc[-1] / base - 1
        return {"total_return": float(total), "cagr": float((1 + total) ** (1 / years) - 1),
                "mdd": float((s / s.cummax() - 1).min())}

    closed = [t for t in trades if t["exit_date"] is not None]
    return {
        "period": f"{idx.iloc[0].date()} ~ {idx.iloc[-1].date()}",
        "bars": int(n - p.warmup),
        "strategy": stats(eq),
        "buy_hold": stats(bh),
        "trades": trades,
        "n_trades": len(trades),
        "win_rate": float(np.mean([t["ret"] > 0 for t in closed])) if closed else None,
        "avg_hold_days": float(np.mean([t["days"] for t in trades])) if trades else None,
        "exposure": float(invested[p.warmup + 1:].mean()),
        "open_position": cur is not None,
    }
