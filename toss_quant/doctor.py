"""연결 점검: 무엇이 안 되는지 쉬운 말로 알려준다."""
import sys

import requests

from .client import TossApiError, TossClient
from .config import Config
from .portfolio import format_table, summarize


def my_ip() -> str:
    try:
        return requests.get("https://api.ipify.org", timeout=8).text.strip()
    except requests.RequestException:
        return "(확인 실패)"


def explain(e: Exception) -> str:
    if isinstance(e, TossApiError):
        if e.status == 403:
            return ("허용 IP가 등록되지 않은 것 같습니다.\n"
                    f"  → 토스증권 앱/웹 '설정 > Open API > 허용 IP 관리'에 이 IP를 등록하세요: {my_ip()}")
        if e.status == 401 or "invalid_client" in e.message:
            return "키(client_id / client_secret)가 틀린 것 같습니다. 복사할 때 앞뒤 공백이 없는지 확인하고 .env를 다시 만드세요."
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
    print(format_table(summarize(result)))
    print("\n모든 점검을 통과했습니다. 이제 Claude와 연결할 수 있습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
