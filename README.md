# toss-quant: 토스증권 Open API × Claude

토스증권 Open API로 보유종목을 조회하고, Claude(MCP)에서 관리하며, 이후 퀀트 매매로 확장하는 프로젝트입니다.

## 진행 단계
| 단계 | 내용 | 상태 |
|---|---|---|
| 1 | API 클라이언트(토큰 캐시·재시도·레이트리밋 대응) | 완료 |
| 2 | 보유종목·잔고 조회 CLI | 완료 |
| 3 | Claude용 MCP 서버(읽기 전용) | 완료 |
| 4 | 시세 수집 + 백테스트 엔진 | 예정 |
| 5 | 전략 구현 + dry-run | 예정 |
| 6 | 실주문(안전장치 필수) | 예정 |

## 사전 준비 (본인 PC에서)
1. 토스증권 WTS → 설정 → Open API 에서 `client_id`/`client_secret` 발급
2. 같은 화면 **허용 IP 관리**에 이 코드를 실행할 PC의 공인 IP 등록 (미등록 IP는 403)
3. `cp .env.example .env` 후 키 입력 (`.env`는 gitignore 처리됨. 절대 커밋 금지)
4. `python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt`

## 사용
```bash
python -m toss_quant.cli accounts
python -m toss_quant.cli holdings
python -m pytest
```

## Claude 연동 (MCP)
Claude Code: `claude mcp add toss -- python -m toss_quant.mcp_server` (저장소 루트에서)
노출 도구: `list_accounts`, `get_holdings`, `get_prices`, `get_open_orders`, `get_buying_power` (조회 전용, 주문 도구 없음)

## IP 가 자주 바뀔 때
`.env` 에 `TOSS_SSH_TUNNEL=user@고정IP서버` (SSH 키 로그인) 또는 `TOSS_PROXY=<프록시 URL>` 을 넣으면 토스증권 요청만 고정 IP 서버를 거칩니다.
허용 IP 에는 그 서버 IP 만 등록하면 됩니다. 자세한 순서는 `시작하기.md` 참고.

## 주의
- 토큰은 클라이언트당 1개만 유효합니다. 여러 프로세스가 각자 발급하면 서로 무효화되므로 `~/.cache/toss_quant/token.json`으로 공유합니다.
- API 데이터는 본인 매매 목적 외 제3자 배포 금지(공식 FAQ).
- 단기간 대량 주문은 어뷰징으로 제한될 수 있습니다.
