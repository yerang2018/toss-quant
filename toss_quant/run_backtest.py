"""보유종목(ETF 제외)에 대해 백테스트를 실행하고 보고서를 만든다.

  python3 -m toss_quant.run_backtest              # 보유종목 중 ETF/ETN 제외
  python3 -m toss_quant.run_backtest --symbols 005930,NVDA
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from .backtest import Params, backtest, market_costs
from .client import TossClient
from .config import Config
from .data import fetch_daily

ETF_TYPES = {"ETF", "FOREIGN_ETF", "ETN"}
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "backtest"


def pick_universe(client: TossClient, symbols: list[str] | None, include_etf: bool = False) -> tuple[list[dict], list[dict]]:
    """(대상, 제외) 종목 정보 목록을 반환한다."""
    if symbols is None:
        holds = client.holdings()["items"]
        symbols = [h["symbol"] for h in holds]
    info = {s["symbol"]: s for s in client.stocks(symbols)} if symbols else {}
    keep, skipped = [], []
    for sym in symbols:
        i = info.get(sym, {"symbol": sym, "name": sym, "securityType": "?", "currency": "USD"})
        (skipped if (i.get("securityType") in ETF_TYPES and not include_etf) else keep).append(i)
    return keep, skipped


def run(client: TossClient, symbols: list[str] | None = None, include_etf: bool = False,
        params: Params | None = None) -> dict:
    keep, skipped = pick_universe(client, symbols, include_etf)
    results, errors = [], []
    for i in keep:
        try:
            df = fetch_daily(client, i["symbol"])
            p = params or Params(**market_costs(i.get("currency", "USD")))
            r = backtest(df, p)
            results.append({"symbol": i["symbol"], "name": i.get("name", i["symbol"]), **r})
        except Exception as e:  # noqa: BLE001  (한 종목 실패가 전체를 막지 않게)
            errors.append({"symbol": i["symbol"], "name": i.get("name", ""), "error": str(e)})
    return {"results": results, "skipped_etf": [f"{s.get('name')}({s['symbol']})" for s in skipped], "errors": errors}


def pct(x) -> str:
    return "-" if x is None else f"{x * 100:+.1f}%"


def format_report(out: dict) -> str:
    L = ["=== 20-60 골든크로스 + 200일선 눌림 전략 백테스트 ===",
         f"{'종목':<14}{'기간':<25}{'전략수익':>9}{'보유수익':>9}{'전략MDD':>9}{'보유MDD':>9}{'거래':>5}{'승률':>7}{'투자비중':>8}"]
    for r in out["results"]:
        L.append(f"{r['name'][:12]:<14}{r['period']:<25}{pct(r['strategy']['total_return']):>9}"
                 f"{pct(r['buy_hold']['total_return']):>9}{pct(r['strategy']['mdd']):>9}{pct(r['buy_hold']['mdd']):>9}"
                 f"{r['n_trades']:>5}{pct(r['win_rate']):>7}{pct(r['exposure']):>8}")
    if out["results"]:
        n = len(out["results"])
        avg = lambda k, f: sum(r[k][f] for r in out["results"]) / n  # noqa: E731
        L += ["", f"평균(동일가중) 전략 {pct(avg('strategy','total_return'))} vs 단순보유 {pct(avg('buy_hold','total_return'))}"
                  f" | MDD 전략 {pct(avg('strategy','mdd'))} vs 보유 {pct(avg('buy_hold','mdd'))}"]
    if out["skipped_etf"]:
        L.append("제외(ETF/ETN): " + ", ".join(out["skipped_etf"]))
    for e in out["errors"]:
        L.append(f"실패: {e['name']}({e['symbol']}) - {e['error']}")
    L += ["", "※ 신호는 종가 확정 후 판단, 체결은 다음 거래일 시가. 수수료·세금·슬리피지는 가정값입니다.",
          "※ 표본 기간이 짧고 거래 횟수가 적어 통계적 신뢰도가 낮습니다. 참고용으로만 보세요."]
    return "\n".join(L)


def save_trades(out: dict) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / "trades.csv"
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["종목", "진입일", "진입가", "진입사유", "청산일", "청산가", "청산사유", "수익률", "보유일"])
        for r in out["results"]:
            for t in r["trades"]:
                w.writerow([r["name"], t["entry_date"].date(), round(t["entry_price"], 4), t["reason"],
                            t["exit_date"].date() if t["exit_date"] is not None else "", round(t["exit_price"], 4),
                            t["exit_reason"], f"{t['ret']:.4f}", t["days"]])
    return path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", help="쉼표로 구분한 종목코드(미지정 시 보유종목)")
    ap.add_argument("--include-etf", action="store_true")
    a = ap.parse_args()
    out = run(TossClient(Config.from_env()), a.symbols.split(",") if a.symbols else None, a.include_etf)
    print(format_report(out))
    print(f"\n매매 내역 저장: {save_trades(out)}")


if __name__ == "__main__":
    main()
