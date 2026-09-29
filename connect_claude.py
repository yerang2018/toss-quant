"""Claude 데스크톱 앱에 토스증권 도구를 자동으로 연결한다: python3 connect_claude.py"""
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def config_path() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/Claude/claude_desktop_config.json"
    if os.name == "nt":
        return Path(os.environ["APPDATA"]) / "Claude" / "claude_desktop_config.json"
    return Path.home() / ".config/Claude/claude_desktop_config.json"


def main(path: Path | None = None) -> None:
    path = path or config_path()
    if not PY.exists():
        sys.exit("먼저 python3 setup.py 를 실행해 설치를 마쳐 주세요.")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if path.exists():
        shutil.copy(path, path.with_suffix(".json.bak"))
        try:
            data = json.loads(path.read_text() or "{}")
        except ValueError:
            sys.exit(f"기존 설정 파일이 손상되어 건드리지 않았습니다: {path}")
    data.setdefault("mcpServers", {})["toss"] = {
        "command": str(PY),
        "args": ["-m", "toss_quant.mcp_server"],
        "env": {"PYTHONPATH": str(ROOT)},
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"✓ 연결 설정을 저장했습니다: {path}")
    print("이제 Claude 앱을 완전히 종료(Cmd+Q)했다가 다시 실행하세요.")
    print('그다음 Claude에게 "내 토스증권 보유종목 보여줘" 라고 말해 보세요.')


if __name__ == "__main__":
    main()
