import argparse
import json

from .client import TossClient
from .config import Config
from .portfolio import format_table, summarize


def main() -> None:
    ap = argparse.ArgumentParser(prog="toss")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("accounts", help="계좌 목록")
    h = sub.add_parser("holdings", help="보유종목 조회")
    h.add_argument("--json", action="store_true")
    args = ap.parse_args()

    client = TossClient(Config.from_env())
    if args.cmd == "accounts":
        for a in client.accounts():
            print(f"accountSeq={a['accountSeq']}  {a['accountNo']}  {a['accountType']}")
    elif args.cmd == "holdings":
        s = summarize(client.holdings())
        print(json.dumps(s, ensure_ascii=False, indent=2) if args.json else format_table(s))


if __name__ == "__main__":
    main()
