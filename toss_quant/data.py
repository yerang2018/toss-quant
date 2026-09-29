"""일봉 캔들 수집(페이지네이션) + CSV 캐시."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .client import TossClient

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "candles"


def fetch_daily(client: TossClient, symbol: str, max_bars: int = 1500, adjusted: bool = True) -> pd.DataFrame:
    """최신→과거 방향으로 200개씩 이어서 받아 시간순 DataFrame(open/high/low/close/volume)으로 반환."""
    rows: list[dict] = []
    before = None
    while len(rows) < max_bars:
        res = client.candles(symbol, "1d", 200, before=before, adjusted=adjusted)
        got = res.get("candles", [])
        rows += got
        before = res.get("nextBefore")
        if not got or not before:
            break
    df = pd.DataFrame(rows)
    if df.empty:
        raise ValueError(f"{symbol}: 캔들 데이터가 없습니다.")
    df["date"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert("Asia/Seoul").dt.tz_localize(None).dt.normalize()
    df = df.rename(columns={"openPrice": "open", "highPrice": "high", "lowPrice": "low",
                            "closePrice": "close"})[["date", "open", "high", "low", "close", "volume"]]
    df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].astype(float)
    df = df.drop_duplicates("date").sort_values("date").reset_index(drop=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(CACHE_DIR / f"{symbol}.csv", index=False)
    return df
