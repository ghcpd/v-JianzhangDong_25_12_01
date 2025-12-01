# Secure Audit Artifacts

## 📁 Overview
- `input_backup.py` — Original insecure source (for comparison/tests)
- `input.py` — Hardened, secure implementation
- `tests/test_security.py` — Security-focused regression tests
- `run_test.sh` / `run_test.bat` — Platform-specific test entrypoints
- `auto_test.py` — Auto-detects OS/Docker, runs tests for both versions, logs results
- `requirements.txt` — Python dependencies
- `setup.sh` — Virtualenv setup & dependency installation (Linux/macOS)
- `Dockerfile` — Reproducible container environment
- `logs/test_run.log` — Test execution log with timestamps and PASS/FAIL status

## ⚙️ Environment Setup
### Linux/macOS
```bash
chmod +x setup.sh run_test.sh
./setup.sh
```

### Windows (PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Docker
```bash
docker build -t secure-audit .
docker run --rm secure-audit
```

## 🧪 Running Tests
- **Linux/macOS:** `./run_test.sh` (uses `TARGET_FILE` env var; defaults to `input.py`)
- **Windows:** `run_test.bat` (uses `TARGET_FILE` env var; defaults to `input.py`)

Examples:
```bash
# Test secure version
TARGET_FILE=input.py ./run_test.sh
# Test backup version
TARGET_FILE=input_backup.py ./run_test.sh
```

## 🤖 Auto Test Runner
```bash
python auto_test.py
```
- Detects OS/Docker automatically
- Runs tests sequentially for `input_backup.py` and `input.py`
- Writes detailed logs and final status to `logs/test_run.log`

## 📜 Logs
- Location: `logs/test_run.log`
- Each run includes: timestamp, target file, stdout/stderr, and `TEST PASSED` or `TEST FAILED`
- Final line summarizes overall status
