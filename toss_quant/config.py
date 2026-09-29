import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_URL = "https://openapi.tossinvest.com"
TOKEN_CACHE = Path(os.environ.get("TOSS_TOKEN_CACHE", Path.home() / ".cache" / "toss_quant" / "token.json"))


@dataclass(frozen=True)
class Config:
    client_id: str
    client_secret: str
    account_seq: int | None = None
    base_url: str = BASE_URL

    @classmethod
    def from_env(cls) -> "Config":
        load_dotenv(Path(__file__).resolve().parent.parent / ".env")
        cid = os.environ.get("TOSS_CLIENT_ID", "").strip()
        secret = os.environ.get("TOSS_CLIENT_SECRET", "").strip()
        if not cid or not secret:
            raise RuntimeError("TOSS_CLIENT_ID / TOSS_CLIENT_SECRET 이 설정되지 않았습니다 (.env 확인).")
        seq = os.environ.get("TOSS_ACCOUNT_SEQ", "").strip()
        return cls(cid, secret, int(seq) if seq else None)
