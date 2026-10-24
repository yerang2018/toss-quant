"""고정 IP 서버로 SSH 터널(SOCKS 프록시)을 자동으로 연다.

집·학교·카페처럼 IP 가 바뀌는 곳에서도, 토스증권에는 항상 고정 IP 서버의 주소로 보이게 한다.
TOSS_SSH_TUNNEL=user@서버주소 를 .env 에 넣으면 첫 요청 때 터널을 띄우고, 이미 떠 있으면 재사용한다.
"""
from __future__ import annotations

import os
import socket
import subprocess
import time

PORT = int(os.environ.get("TOSS_SSH_PORT", "1080"))


def _listening(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False


def ensure(target: str, port: int = PORT, wait: float = 15.0) -> str:
    """터널이 열려 있게 하고 requests 용 프록시 주소를 돌려준다."""
    proxy = f"socks5h://127.0.0.1:{port}"
    if _listening(port):
        return proxy
    # BatchMode: 비밀번호를 묻느라 Claude 가 멈추지 않도록 SSH 키 로그인만 허용한다.
    subprocess.Popen(
        ["ssh", "-N", "-D", f"127.0.0.1:{port}", "-o", "BatchMode=yes", "-o", "ExitOnForwardFailure=yes",
         "-o", "ServerAliveInterval=30", "-o", "ServerAliveCountMax=3", "-o", "StrictHostKeyChecking=accept-new",
         target],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
    )
    deadline = time.time() + wait
    while time.time() < deadline:
        if _listening(port):
            return proxy
        time.sleep(0.3)
    raise RuntimeError(f"고정 IP 서버({target})로 SSH 터널을 열지 못했습니다. "
                       f"터미널에서 'ssh {target}' 가 비밀번호 없이 접속되는지 확인하세요.")
