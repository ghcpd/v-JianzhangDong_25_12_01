import os
import subprocess
import platform
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "test_run.log"
ROOT_DIR = Path(__file__).parent.resolve()


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def detect_env():
    system = platform.system().lower()
    is_docker = Path("/.dockerenv").exists() or os.environ.get("DOCKER") == "1"
    return system, is_docker


def run_test_script(target_file: str):
    system, is_docker = detect_env()
    env = os.environ.copy()
    env["TARGET_FILE"] = target_file

    if system == "windows":
        cmd = ["cmd", "/c", "run_test.bat"]
    else:
        cmd = ["bash", "run_test.sh"]

    proc = subprocess.run(
        cmd,
        cwd=ROOT_DIR,
        env=env,
        capture_output=True,
        text=True,
    )
    return {
        "target": target_file,
        "system": system,
        "is_docker": is_docker,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def log_result(result: dict):
    lines = []
    lines.append("===== TEST START =====")
    lines.append(f"timestamp: {timestamp()}")
    lines.append(f"target_file: {result['target']}")
    lines.append(f"system: {result['system']}")
    lines.append(f"is_docker: {result['is_docker']}")
    lines.append("--- stdout ---")
    lines.append(result.get("stdout", ""))
    lines.append("--- stderr ---")
    lines.append(result.get("stderr", ""))
    status_line = "TEST PASSED" if result.get("returncode") == 0 else "TEST FAILED"
    lines.append(status_line)
    lines.append("===== TEST END =====\n")
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return status_line


def main():
    targets = ["input_backup.py", "input.py"]
    overall_pass = True
    for target in targets:
        result = run_test_script(target)
        status_line = log_result(result)
        if result.get("returncode") != 0:
            overall_pass = False
    final_status = "TEST PASSED" if overall_pass else "TEST FAILED"
    with LOG_FILE.open("a") as f:
        f.write(f"FINAL STATUS: {final_status}\n")
    print(final_status)
    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
