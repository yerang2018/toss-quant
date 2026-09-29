"""보유종목 요약/분석. 금액은 API 가 문자열로 주므로 Decimal 로 계산한다."""
from __future__ import annotations

from decimal import Decimal


def _d(x) -> Decimal:
    return Decimal(str(x)) if x not in (None, "") else Decimal(0)


def summarize(holdings: dict) -> dict:
    """weight(평가금액 비중)를 포함한 종목별 요약과 합계를 만든다."""
    items = holdings.get("items", [])
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
    def both(node):
        return {"krw": node["krw"], "usd": node.get("usd")}

    # 합계 필드는 통화별로 나뉘어 온다(krw=국내분, usd=미국분). 종목별 값으로 시장별 소계도 직접 계산한다.
    by_market: dict[str, dict] = {}
    for it in items:
        m = by_market.setdefault(it["marketCountry"], {"currency": it["currency"], "market_value": Decimal(0),
                                                        "purchase": Decimal(0), "count": 0})
        m["market_value"] += _d(it["marketValue"]["amount"])
        m["purchase"] += _d(it["marketValue"]["purchaseAmount"])
        m["count"] += 1
    for m in by_market.values():
        m["pnl"] = m["market_value"] - m["purchase"]
        m["pnl_rate"] = str((m["pnl"] / m["purchase"]).quantize(Decimal("0.0001"))) if m["purchase"] else "0"
        m["market_value"], m["purchase"], m["pnl"] = str(m["market_value"]), str(m["purchase"]), str(m["pnl"])

    return {
        "note": "합계는 통화별로 분리되어 있습니다(KRW=국내, USD=미국). 원화 합산은 환율 적용이 필요합니다.",
        "total_market_value": both(holdings["marketValue"]["amount"]),
        "total_purchase": both(holdings["totalPurchaseAmount"]),
        "total_pnl": both(holdings["profitLoss"]["amount"]),
        "daily_pnl": both(holdings["dailyProfitLoss"]["amount"]),
        "by_market": by_market,
        "count": len(rows),
        "items": rows,
    }


def format_table(summary: dict) -> str:
    lines = []
    for mk, m in summary["by_market"].items():
        lines.append(f"[{mk}] {m['count']}종목 평가 {m['market_value']} {m['currency']} | 손익 {m['pnl']} ({m['pnl_rate']})")
    lines += ["", f"{'종목':<14}{'수량':>8}{'평균단가':>12}{'현재가':>12}{'수익률':>10}"]
    for r in summary["items"]:
        lines.append(f"{r['name'][:12]:<14}{r['quantity']:>8}{r['avg_price']:>12}{r['last_price']:>12}"
                     f"{r['pnl_rate']:>10}")
    return "\n".join(lines)
