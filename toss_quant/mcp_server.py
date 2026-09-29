"""Claude 용 MCP 서버 (읽기 전용). 주문 도구는 의도적으로 노출하지 않는다.

Claude Desktop / Claude Code 설정 예:
  {"mcpServers": {"toss": {"command": "python", "args": ["-m", "toss_quant.mcp_server"],
                           "cwd": "/path/to/repo"}}}
"""
from mcp.server.fastmcp import FastMCP

from .client import TossClient
from .config import Config
from .portfolio import summarize

mcp = FastMCP("toss-securities")
_client: TossClient | None = None


def client() -> TossClient:
    global _client
    if _client is None:
        _client = TossClient(Config.from_env())
    return _client


@mcp.tool()
def list_accounts() -> list[dict]:
    """토스증권 계좌 목록(accountSeq 포함)을 조회합니다."""
    return client().accounts()


@mcp.tool()
def get_holdings() -> dict:
    """보유종목과 합산 평가금액·손익을 요약해서 반환합니다."""
    c = client()
    return summarize(c.holdings(), c.exchange_rate()["rate"])


@mcp.tool()
def get_prices(symbols: list[str]) -> list[dict]:
    """현재가 조회. KR은 6자리 종목코드(005930), US는 티커(AAPL). 최대 200개."""
    return client().prices(symbols)


@mcp.tool()
def get_open_orders() -> dict:
    """체결 대기 중인 주문 목록을 조회합니다."""
    return client().orders("OPEN")


@mcp.tool()
def get_buying_power(currency: str = "KRW") -> dict:
    """현금 기반 매수 가능 금액 (KRW 또는 USD)."""
    return client().buying_power(currency)


if __name__ == "__main__":
    mcp.run()
