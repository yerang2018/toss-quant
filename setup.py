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


def main():
    print("[1/3] 필요한 프로그램 설치 중 (1~2분 걸립니다)...")
    if not PY.exists():
        venv.create(VENV, with_pip=True)
    run("-m", "pip", "install", "-q", "-r", "requirements.txt")

    env = ROOT / ".env"
    if not env.exists():
        print("\n[2/3] 토스증권 키를 입력하세요. (입력해도 화면에 안 보이는 게 정상입니다)")
        cid = getpass.getpass("  client_id: ").strip()
        secret = getpass.getpass("  client_secret: ").strip()
        env.write_text(f"TOSS_CLIENT_ID={cid}\nTOSS_CLIENT_SECRET={secret}\nTOSS_ACCOUNT_SEQ=\n")
        try:
            env.chmod(0o600)
        except OSError:
            pass
        print("  → .env 파일에 저장했습니다 (이 컴퓨터에만 있고 인터넷에 올라가지 않습니다).")
    else:
        print("\n[2/3] 기존 .env 파일을 사용합니다.")

    print("\n[3/3] 토스증권 연결을 점검합니다...\n")
    sys.exit(subprocess.call([str(PY), "-m", "toss_quant.doctor"], cwd=ROOT))


if __name__ == "__main__":
    main()
