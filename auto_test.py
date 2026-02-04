import os
import sys
import subprocess
import datetime
import platform

LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'test_run.log')

MODULES = ['input_backup', 'inputs']

def detect_environment():
    if os.path.exists('/.dockerenv'):
        return 'docker'
    if os.name == 'nt' or platform.system() == 'Windows':
        return 'windows'
    return 'linux'


def run_script(command, shell=False):
    proc = subprocess.Popen(command, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    stdout, _ = proc.communicate()
    return proc.returncode, stdout


def log(msg):
    ts = datetime.datetime.utcnow().isoformat() + 'Z'
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"[{ts}] {msg}\n")


def main():
    env = detect_environment()
    log(f"Environment detected: {env}")
    overall_success = True

    # Run tests for both modules
    for module in MODULES:
        log(f"Running test for module: {module}")
        # Choose correct test runner based on OS
        if env == 'windows':
            cmd = ['cmd', '/c', 'run_test.bat', module]
        else:
            cmd = ['bash', 'run_test.sh', module]

        rc, out = run_script(cmd)
        log(out)
        status = 'TEST PASSED' if rc == 0 else 'TEST FAILED'
        log(f"{module}: exit_code={rc} status={status}")

        # We expect input_backup to be vulnerable (non-zero exit) and inputs to pass (zero exit)
        if module == 'input_backup' and rc == 0:
            overall_success = False
        if module == 'inputs' and rc != 0:
            overall_success = False

    final_status = 'TEST PASSED' if overall_success else 'TEST FAILED'
    log(f"Final result: {final_status}")
    print(final_status)
    return 0 if overall_success else 1


if __name__ == '__main__':
    rc = main()
    sys.exit(rc)
