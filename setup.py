"""처음 한 번만 실행: python setup.py  (설치 + 키 입력 + 연결 점검을 자동으로 진행)"""
import getpass
import os
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).parent
VENV = ROOT / ".venv"
PY = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def run(*args):
    subprocess.check_call([str(PY), *args], cwd=ROOT)


HOME_ENV = Path.home() / ".toss_quant" / ".env"


def save_env(text: str) -> None:
    for target in (ROOT / ".env", HOME_ENV):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
        try:
            target.chmod(0o600)
        except OSError:
            pass


def find_old_env() -> str | None:
    """이전에 받은 폴더에 저장된 키를 찾는다(내용은 화면에 표시하지 않는다)."""
    found = [HOME_ENV] if HOME_ENV.exists() else []
    for base in ("Downloads", "Desktop", "Documents"):
        found += sorted((Path.home() / base).glob("*/.env"))
    for f in found:
        try:
            text = f.read_text()
        except OSError:
            continue
        vals = dict(l.split("=", 1) for l in text.splitlines() if "=" in l)
        if vals.get("TOSS_CLIENT_ID", "").strip() and vals.get("TOSS_CLIENT_SECRET", "").strip():
            return text
    return None


def main():
    print("[1/3] 필요한 프로그램 설치 중 (1~2분 걸립니다)...")
    if not PY.exists():
        venv.create(VENV, with_pip=True)
    run("-m", "pip", "install", "-q", "-r", "requirements.txt")

    env = ROOT / ".env"
    if not env.exists():
        old = find_old_env()
        if old and input("\n이전에 저장한 토스증권 키를 찾았습니다. 그대로 사용할까요? (y/n): ").strip().lower() == "y":
            save_env(old)
            print("  → 이전 키를 사용합니다. 다시 입력하지 않아도 됩니다.")
    if not env.exists():
        print("\n[2/3] 토스증권 키를 입력하세요. (입력해도 화면에 안 보이는 게 정상입니다)")
        cid = getpass.getpass("  client_id: ").strip()
        secret = getpass.getpass("  client_secret: ").strip()
        save_env(f"TOSS_CLIENT_ID={cid}\nTOSS_CLIENT_SECRET={secret}\nTOSS_ACCOUNT_SEQ=\n")
        print("  → .env 파일에 저장했습니다 (이 컴퓨터에만 있고 인터넷에 올라가지 않습니다).")
    else:
        print("\n[2/3] 기존 .env 파일을 사용합니다.")

    print("\n[3/3] 토스증권 연결을 점검합니다...\n")
    sys.exit(subprocess.call([str(PY), "-m", "toss_quant.doctor"], cwd=ROOT))


if __name__ == "__main__":
    main()
