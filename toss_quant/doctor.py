"""연결 점검: 무엇이 안 되는지 쉬운 말로 알려준다."""
import sys

import requests

from .client import TossApiError, TossClient
from .config import Config
from .portfolio import format_table, summarize


def my_ip() -> str:
    """IPv4 와 IPv6 를 모두 보여준다. 네트워크가 IPv6 를 쓰면 토스증권에는 IPv6 주소로 보일 수 있다."""
    out = []
    for label, url in (("IPv4", "https://api.ipify.org"), ("IPv6", "https://api6.ipify.org")):
        try:
            out.append(f"{label} {requests.get(url, timeout=8).text.strip()}")
        except requests.RequestException:
            out.append(f"{label} 없음")
    return " / ".join(out)


def explain(e: Exception) -> str:
    if isinstance(e, TossApiError):
        raw = f"(서버 응답: {e.status} {e.code} - {e.message})"
        if e.status == 403:
            return ("허용 IP 문제일 가능성이 높습니다. " + raw + "\n"
                    f"  → 지금 주소: {my_ip()}\n"
                    "  → 토스증권 '설정 > Open API > 허용 IP 관리'에 위 주소가 있는지 확인하세요.\n"
                    "    IPv4가 이미 등록되어 있는데도 막히면 IPv6 주소도 등록해 보세요.")
        if e.status == 401 or "invalid_client" in e.message:
            return ("인증 문제입니다. " + f"(서버 응답: {e.status} {e.code})" + "\n"
                    "  → token-revoked 면 다른 곳에서 토큰을 새로 받은 것이니 다시 실행하면 됩니다.\n"
                    "  → invalid_client 면 키가 틀린 것입니다. rm .env 후 python3 setup.py 로 다시 입력하세요.")
        if e.status == 429:
            return "요청이 너무 많았습니다. 잠시 후 다시 실행하세요."
        return f"토스증권 서버 응답 오류: {e}"
    return f"예상치 못한 오류: {e}"


def main() -> int:
    print("1) 설정 파일(.env) 읽는 중...")
    try:
        client = TossClient(Config.from_env())
    except RuntimeError as e:
        print("  ✗", e)
        return 1
    print("  ✓ 키를 읽었습니다.")
    steps = [("2) 토큰 발급", lambda: client.token(force=True)),
             ("3) 계좌 조회", client.accounts),
             ("4) 보유종목 조회", client.holdings)]
    result = None
    for title, fn in steps:
        print(title, "...")
        try:
            result = fn()
            print("  ✓ 성공")
        except Exception as e:  # noqa: BLE001
            print("  ✗ 실패\n ", explain(e))
            return 1
    print("\n===== 내 보유종목 =====")
    print(format_table(summarize(result, client.exchange_rate()["rate"])))
    print("\n모든 점검을 통과했습니다. 이제 Claude와 연결할 수 있습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
