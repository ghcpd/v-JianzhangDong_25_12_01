# Secure Audit and Test Suite for inputs.py

Overview

- `inputs.py`: Secured version of the original application.
- `input_backup.py`: Original file preserved for auditing and testing.
- `report.json`: Audit report listing vulnerabilities and fixes.
- `tests/test_runner.py`: Automated tests that detect the vulnerabilities present in `input_backup.py` and verify fixes in `inputs.py`.
- `auto_test.py`: Runs tests for both `input_backup.py` and `inputs.py`, logs results to `logs/test_run.log`, and prints final status.
- `requirements.txt`: Python dependencies.
- `setup.sh`: Environment setup script for Linux/macOS (creates venv and installs dependencies).
- `run_test.sh` / `run_test.bat`: Run tests for a specific module (default `inputs`).
- `Dockerfile`: Minimal Docker image for the app.

Setup

Linux / macOS

1. Create and activate virtual environment:

   ./setup.sh

2. Ensure the following environment variables are set (required):

   - `API_KEY` - API key used to authenticate sensitive endpoints
   - `INTERNAL_AUTH` - HMAC secret used for token generation
   - `WEBHOOK_SECRET` - Secret used to sign webhook payloads

   Optional:
   - `PAYMENT_TOKEN`, `MAIL_SERVER_KEY` - loaded from env if needed.

Windows

1. Create virtual environment & install requirements (manual):

   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt

2. Set the required environment variables (PowerShell):

   $env:API_KEY = "YOUR_API_KEY"
   $env:INTERNAL_AUTH = "YOUR_INTERNAL_AUTH"
   $env:WEBHOOK_SECRET = "YOUR_WEBHOOK_SECRET"

Running Tests

Linux/macOS

- Run tests against one module: `./run_test.sh inputs` or `./run_test.sh input_backup`.
- Run the auto-test: `python auto_test.py` (will run both `input_backup` and `inputs`, logging to `logs/test_run.log`).

Windows

- Run tests: `run_test.bat inputs`.
- Run auto-test: `python auto_test.py` (auto-detects platform and runs correct commands).

Interpreting Logs

- `logs/test_run.log` will contain time-stamped outputs of each test run and a final status line: `TEST PASSED` or `TEST FAILED`.
- `TEST PASSED` indicates:
  - `input_backup.py` demonstrated the expected vulnerabilities (non-zero exit), and
  - `inputs.py` did NOT show these vulnerabilities (zero exit).
- `TEST FAILED` indicates either the patched version still has a vulnerability or the backup did not show expected issues.

Notes & Security Considerations

- Secrets must not be stored in source control. Initialize the required env vars before running.
- The tests do not make network calls - `requests.post` is monkeypatched to intercept calls.
- The scripts are designed to be idempotent and safe; no destructive operations are performed.

If you need further assistance or want me to add stricter checks or additional tests (e.g., unit tests for endpoints), tell me which parts to extend.
