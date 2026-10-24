"""토스증권 Open API REST 클라이언트.

- 토큰은 클라이언트당 1개만 유효(재발급 시 이전 토큰 무효화)하므로 파일에 캐시해 프로세스 간 공유한다.
- 429 는 Retry-After 를 존중하며 재시도, 401 은 토큰을 1회 재발급 후 재시도한다.
"""
from __future__ import annotations

import json
import os
import socket
import time
from typing import Any

import requests
import urllib3.util.connection as _u3conn

# 허용 IP 는 보통 IPv4 로 등록한다. IPv6 를 지원하는 네트워크(학교 등)에서는 IPv6 로 접속되어
# 등록된 IPv4 와 달라 403 이 날 수 있으므로 기본적으로 IPv4 로만 접속한다. (TOSS_FORCE_IPV4=0 으로 해제)
if os.environ.get("TOSS_FORCE_IPV4", "1") != "0":
    _u3conn.allowed_gai_family = lambda: socket.AF_INET

from .config import TOKEN_CACHE, Config


class TossApiError(Exception):
    def __init__(self, status: int, code: str, message: str, request_id: str | None = None):
        super().__init__(f"[{status}] {code}: {message} (requestId={request_id})")
        self.status, self.code, self.message, self.request_id = status, code, message, request_id


class TossClient:
    def __init__(self, config: Config, session: requests.Session | None = None):
        self.cfg = config
        self.http = session or requests.Session()
        self._account_seq = config.account_seq

    # ---- 인증 ----
    def _load_cached_token(self) -> str | None:
        try:
            data = json.loads(TOKEN_CACHE.read_text())
            if data["client_id"] == self.cfg.client_id and data["expires_at"] > time.time() + 60:
                return data["access_token"]
        except (OSError, ValueError, KeyError):
            pass
        return None

    def _issue_token(self) -> str:
        r = self.http.post(
            f"{self.cfg.base_url}/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.cfg.client_id,
                "client_secret": self.cfg.client_secret,
            },
            timeout=15,
        )
        if r.status_code != 200:
            raise TossApiError(r.status_code, "token-error", r.text[:300])
        body = r.json()
        token = body["access_token"]
        TOKEN_CACHE.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(TOKEN_CACHE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(
                {"client_id": self.cfg.client_id, "access_token": token,
                 "expires_at": time.time() + int(body["expires_in"])},
                f,
            )
        return token

    def token(self, force: bool = False) -> str:
        if not force:
            cached = self._load_cached_token()
            if cached:
                return cached
        return self._issue_token()

    # ---- 요청 ----
    def request(self, method: str, path: str, *, params: dict | None = None, json_body: Any = None,
                account: bool = False, max_retries: int = 4) -> Any:
        refreshed = False
        for attempt in range(max_retries + 1):
            headers = {"Authorization": f"Bearer {self.token()}"}
            if account:
                headers["X-Tossinvest-Account"] = str(self.account_seq())
            r = self.http.request(method, f"{self.cfg.base_url}{path}", params=params,
                                  json=json_body, headers=headers, timeout=15)
            if r.status_code == 429 and attempt < max_retries:
                time.sleep(float(r.headers.get("Retry-After", 2 ** attempt)))
                continue
            if r.status_code == 401 and not refreshed:
                refreshed = True
                self.token(force=True)
                continue
            if r.status_code >= 500 and attempt < max_retries:
                time.sleep(2 ** attempt)
                continue
            if r.status_code >= 400:
                try:
                    err = r.json().get("error", {})
                except ValueError:
                    err = {}
                raise TossApiError(r.status_code, err.get("code", ""), err.get("message", r.text[:200]),
                                   err.get("requestId"))
            body = r.json()
            return body.get("result", body) if isinstance(body, dict) else body
        raise TossApiError(429, "retry-exhausted", "재시도 횟수 초과")

    # ---- 계좌·자산 ----
    def accounts(self) -> list[dict]:
        return self.request("GET", "/api/v1/accounts")

    def account_seq(self) -> int:
        if self._account_seq is None:
            accts = self.accounts()
            if not accts:
                raise RuntimeError("조회 가능한 계좌가 없습니다.")
            self._account_seq = int(accts[0]["accountSeq"])
        return self._account_seq

    def holdings(self, symbol: str | None = None) -> dict:
        return self.request("GET", "/api/v1/holdings", params={"symbol": symbol} if symbol else None,
                            account=True)

    # ---- 시세 ----
    def prices(self, symbols: list[str]) -> list[dict]:
        return self.request("GET", "/api/v1/prices", params={"symbols": ",".join(symbols)})

    def stocks(self, symbols: list[str]) -> list[dict]:
        return self.request("GET", "/api/v1/stocks", params={"symbols": ",".join(symbols)})

    def exchange_rate(self, base: str = "USD", quote: str = "KRW") -> dict:
        return self.request("GET", "/api/v1/exchange-rate", params={"baseCurrency": base, "quoteCurrency": quote})

    def candles(self, symbol: str, interval: str = "1d", count: int = 200, before: str | None = None,
                adjusted: bool = True) -> dict:
        p = {"symbol": symbol, "interval": interval, "count": count, "adjusted": str(adjusted).lower()}
        if before:
            p["before"] = before
        return self.request("GET", "/api/v1/candles", params=p)

    # ---- 주문 조회(읽기 전용) ----
    def orders(self, status: str = "OPEN", symbol: str | None = None, limit: int = 20) -> dict:
        p: dict = {"status": status}
        if symbol:
            p["symbol"] = symbol
        if status == "CLOSED":
            p["limit"] = limit
        return self.request("GET", "/api/v1/orders", params=p, account=True)

    def buying_power(self, currency: str = "KRW") -> dict:
        return self.request("GET", "/api/v1/buying-power", params={"currency": currency}, account=True)
