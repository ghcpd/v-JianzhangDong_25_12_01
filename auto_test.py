import os
import subprocess
import sys
import platform
import datetime
import json

LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'test_run.log')

os.makedirs(LOG_DIR, exist_ok=True)


def now():
    return datetime.datetime.utcnow().isoformat() + 'Z'


def run_script(script):
    # Run the given script and return completed process
    proc = subprocess.run(script, shell=True, capture_output=True, text=True)
    return proc


def main():
    if platform.system().lower().startswith('win'):
        script = 'run_test.bat'
    else:
        script = './run_test.sh'

    with open(LOG_FILE, 'a') as logf:
        start_ts = now()
        logf.write(f"[{start_ts}] Starting test runner: {script}\n")
        proc = run_script(script)
        logf.write(f"[{now()}] Return code: {proc.returncode}\n")
        logf.write(f"[{now()}] STDOUT:\n{proc.stdout}\n")
        logf.write(f"[{now()}] STDERR:\n{proc.stderr}\n")

        # Parse tests_report.json if present
        report_path = os.path.join(os.path.dirname(__file__), 'tests_report.json')
        if os.path.exists(report_path):
            try:
                with open(report_path) as f:
                    report = json.load(f)
                logf.write(f"[{now()}] Test report: {json.dumps(report, indent=2)}\n")
                # Determine pass/fail per module
                overall = True
                for mod, dat in report.items():
                    passed = dat.get('passed', False)
                    logf.write(f"[{now()}] Module {mod}: passed={passed}, vuln_score={dat.get('vuln_score')}\n")
                    overall = overall and passed
                final_status = 'TEST PASSED' if overall else 'TEST FAILED'
            except Exception as e:
                logf.write(f"[{now()}] Failed to parse test report: {e}\n")
                final_status = 'TEST FAILED'
        else:
            final_status = 'TEST FAILED'

        logf.write(f"[{now()}] {final_status}\n")

    # Also print final status for the CI
    print(final_status)
    sys.exit(0 if final_status == 'TEST PASSED' else 1)


if __name__ == '__main__':
    main()
