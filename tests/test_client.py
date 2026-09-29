import json
import time

import pytest

from toss_quant import client as client_mod
from toss_quant.client import TossApiError, TossClient
from toss_quant.config import Config
from toss_quant.portfolio import summarize

HOLDINGS = {"result": {
    "totalPurchaseAmount": {"krw": "1000000", "usd": None},
    "marketValue": {"amount": {"krw": "1100000", "usd": None}, "amountAfterCost": {"krw": "1099000", "usd": None}},
    "profitLoss": {"amount": {"krw": "100000", "usd": None}, "amountAfterCost": {"krw": "99000", "usd": None},
                   "rate": "0.1", "rateAfterCost": "0.099"},
    "dailyProfitLoss": {"amount": {"krw": "5000", "usd": None}, "rate": "0.004"},
    "items": [{"symbol": "005930", "name": "삼성전자", "marketCountry": "KR", "currency": "KRW",
               "quantity": "10", "lastPrice": "110000", "averagePurchasePrice": "100000",
               "marketValue": {"purchaseAmount": "1000000", "amount": "1100000", "amountAfterCost": "1099000"},
               "profitLoss": {"amount": "100000", "amountAfterCost": "99000", "rate": "0.1", "rateAfterCost": "0.099"},
               "dailyProfitLoss": {"amount": "5000", "rate": "0.004"},
               "cost": {"commission": "1000", "tax": None}}]}}


class Resp:
    def __init__(self, status, body, headers=None):
        self.status_code, self._b, self.headers, self.text = status, body, headers or {}, json.dumps(body)

    def json(self):
        return self._b


class FakeSession:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []

    def post(self, url, **kw):
        self.calls.append(("POST", url, kw))
        return self.responses.pop(0)

    def request(self, method, url, **kw):
        self.calls.append((method, url, kw))
        return self.responses.pop(0)


@pytest.fixture(autouse=True)
def tmp_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(client_mod, "TOKEN_CACHE", tmp_path / "token.json")
    monkeypatch.setattr(time, "sleep", lambda s: None)


CFG = Config("id", "secret", account_seq=1)
TOKEN = Resp(200, {"access_token": "T1", "token_type": "Bearer", "expires_in": 3600})


def test_holdings_sends_account_header_and_summarizes():
    s = FakeSession([TOKEN, Resp(200, HOLDINGS)])
    data = TossClient(CFG, s).holdings()
    hdrs = s.calls[1][2]["headers"]
    assert hdrs["Authorization"] == "Bearer T1" and hdrs["X-Tossinvest-Account"] == "1"
    out = summarize(data)
    assert out["items"][0]["name"] == "삼성전자"
    assert out["by_market"]["KR"]["market_value"] == "1100000" and out["total_market_value"]["krw"] == "1100000"


def test_token_cached_and_reissued_on_401():
    s = FakeSession([TOKEN, Resp(401, {"error": {"code": "expired-token"}}),
                     Resp(200, {"access_token": "T2", "token_type": "Bearer", "expires_in": 3600}),
                     Resp(200, {"result": []})])
    TossClient(CFG, s).prices(["005930"])
    assert s.calls[-1][2]["headers"]["Authorization"] == "Bearer T2"


def test_429_retry_after_then_success():
    s = FakeSession([TOKEN, Resp(429, {}, {"Retry-After": "1"}), Resp(200, {"result": []})])
    assert TossClient(CFG, s).prices(["AAPL"]) == []


def test_error_envelope_raises():
    s = FakeSession([TOKEN, Resp(403, {"error": {"requestId": "r1", "code": "edge-blocked", "message": "x"}})])
    with pytest.raises(TossApiError) as e:
        TossClient(CFG, s).accounts()
    assert e.value.code == "edge-blocked" and e.value.status == 403


def test_combined_krw_with_usd_holdings():
    h = json.loads(json.dumps(HOLDINGS["result"]))
    h["marketValue"]["amount"]["usd"] = "100"
    h["totalPurchaseAmount"]["usd"] = "90"
    h["items"].append({**h["items"][0], "symbol": "AAPL", "name": "애플", "marketCountry": "US", "currency": "USD",
                       "marketValue": {"purchaseAmount": "90", "amount": "100", "amountAfterCost": "100"}})
    c = summarize(h, "1400")["combined_krw"]
    assert c["market_value_krw"] == str(1100000 + 100 * 1400)
    assert c["purchase_krw"] == str(1000000 + 90 * 1400)
