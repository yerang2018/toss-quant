import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_URL = "https://openapi.tossinvest.com"
HOME_ENV = Path.home() / ".toss_quant" / ".env"
TOKEN_CACHE = Path(os.environ.get("TOSS_TOKEN_CACHE", Path.home() / ".cache" / "toss_quant" / "token.json"))


@dataclass(frozen=True)
class Config:
    client_id: str
    client_secret: str
    account_seq: int | None = None
    base_url: str = BASE_URL
    # 고정 IP 서버를 거쳐 접속할 때 사용 (집 IP 가 바뀌어도 허용 IP 를 다시 등록하지 않아도 됨)
    proxy: str | None = None
    ssh_tunnel: str | None = None

    @classmethod
    def from_env(cls) -> "Config":
        load_dotenv(Path(__file__).resolve().parent.parent / ".env")
        load_dotenv(HOME_ENV)
        cid = os.environ.get("TOSS_CLIENT_ID", "").strip()
        secret = os.environ.get("TOSS_CLIENT_SECRET", "").strip()
        if not cid or not secret:
            raise RuntimeError("TOSS_CLIENT_ID / TOSS_CLIENT_SECRET 이 설정되지 않았습니다 (.env 확인).")
        seq = os.environ.get("TOSS_ACCOUNT_SEQ", "").strip()
        proxy = os.environ.get("TOSS_PROXY", "").strip() or None
        tunnel = os.environ.get("TOSS_SSH_TUNNEL", "").strip() or None
        return cls(cid, secret, int(seq) if seq else None, proxy=proxy, ssh_tunnel=tunnel)
