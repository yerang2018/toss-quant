"""보유종목 요약/분석. 금액은 API 가 문자열로 주므로 Decimal 로 계산한다."""
from __future__ import annotations

from decimal import Decimal


def _d(x) -> Decimal:
    return Decimal(str(x)) if x not in (None, "") else Decimal(0)


def summarize(holdings: dict) -> dict:
    """weight(평가금액 비중)를 포함한 종목별 요약과 합계를 만든다."""
    items = holdings.get("items", [])
    total_krw = _d(holdings["marketValue"]["amount"]["krw"])
    rows = []
    for it in items:
        rows.append({
            "symbol": it["symbol"],
            "name": it["name"],
            "market": it["marketCountry"],
            "currency": it["currency"],
            "quantity": it["quantity"],
            "avg_price": it["averagePurchasePrice"],
            "last_price": it["lastPrice"],
            "market_value": it["marketValue"]["amount"],
            "pnl": it["profitLoss"]["amount"],
            "pnl_rate": it["profitLoss"]["rate"],
            "daily_pnl_rate": it["dailyProfitLoss"]["rate"],
        })
    return {
        "total_market_value_krw": str(total_krw),
        "total_purchase_krw": holdings["totalPurchaseAmount"]["krw"],
        "total_pnl_krw": holdings["profitLoss"]["amount"]["krw"],
        "total_pnl_rate": holdings["profitLoss"]["rate"],
        "daily_pnl_krw": holdings["dailyProfitLoss"]["amount"]["krw"],
        "count": len(rows),
        "items": rows,
    }


def format_table(summary: dict) -> str:
    lines = [f"총 평가 {summary['total_market_value_krw']}원 | 손익 {summary['total_pnl_krw']}원 "
             f"({summary['total_pnl_rate']}) | 일간 {summary['daily_pnl_krw']}원", ""]
    lines.append(f"{'종목':<14}{'수량':>8}{'평균단가':>12}{'현재가':>12}{'수익률':>10}")
    for r in summary["items"]:
        lines.append(f"{r['name'][:12]:<14}{r['quantity']:>8}{r['avg_price']:>12}{r['last_price']:>12}"
                     f"{r['pnl_rate']:>10}")
    return "\n".join(lines)
