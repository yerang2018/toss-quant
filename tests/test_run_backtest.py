import numpy as np
import pandas as pd

from toss_quant import data as data_mod
from toss_quant import run_backtest as rb
from toss_quant.run_backtest import format_report, run
from tests.test_backtest import wave


class FakeClient:
    def holdings(self):
        return {"items": [{"symbol": s} for s in ("AAA", "ETF1", "BBB")]}

    def stocks(self, symbols):
        t = {"AAA": ("STOCK", "KRW"), "ETF1": ("ETF", "KRW"), "BBB": ("FOREIGN_STOCK", "USD")}
        return [{"symbol": s, "name": f"이름{s}", "securityType": t[s][0], "currency": t[s][1]} for s in symbols]

    def candles(self, symbol, interval, count, before=None, adjusted=True):
        n = 700
        c = wave(n) + (5 if symbol == "BBB" else 0)
        dates = pd.date_range("2022-01-03", periods=n, freq="B")
        allrows = [{"timestamp": d.isoformat() + "+09:00", "openPrice": str(v), "highPrice": str(v * 1.01),
                    "lowPrice": str(v * 0.99), "closePrice": str(v), "volume": "1000", "currency": "KRW"}
                   for d, v in zip(dates, c)][::-1]  # 최신순
        start = 0 if before is None else next(i for i, r in enumerate(allrows) if r["timestamp"] <= before)
        page = allrows[start:start + count]
        nxt = allrows[start + count]["timestamp"] if start + count < len(allrows) else None
        return {"candles": page, "nextBefore": nxt}


def test_universe_excludes_etf_and_pagination_reassembles(tmp_path, monkeypatch):
    monkeypatch.setattr(data_mod, "CACHE_DIR", tmp_path)
    out = run(FakeClient())
    names = [r["symbol"] for r in out["results"]]
    assert names == ["AAA", "BBB"] and out["skipped_etf"] == ["이름ETF1(ETF1)"]
    assert not out["errors"]
    assert out["results"][0]["bars"] == 700 - 200            # 200개씩 3페이지가 빠짐없이 이어짐
    txt = format_report(out)
    assert "제외(ETF/ETN)" in txt and "평균" in txt
    monkeypatch.setattr(rb, "OUT_DIR", tmp_path)
    assert rb.save_trades(out).exists()
