import os
import platform
import subprocess
import shlex
import datetime

LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'test_run.log')

SCRIPTS = {
    'Linux': './run_test.sh',
    'Darwin': './run_test.sh',
    'Windows': 'run_test.bat'
}

MODULES = ['backup', 'fixed']


def run_script(script, module):
    # script path
    cmd = None
    system = platform.system()
    if system == 'Windows':
        cmd = [script, module]
    else:
        cmd = ['bash', script, module]
    process = subprocess.run(cmd, capture_output=True, text=True)
    return process.returncode, process.stdout + process.stderr


def main():
    system = platform.system()
    script = SCRIPTS.get(system)
    if not script:
        print(f'Unsupported OS: {system}')
        return 2

    overall_success = True
    with open(LOG_FILE, 'a', encoding='utf-8') as fh:
        fh.write('---\n')
        fh.write(f'Test run started: {datetime.datetime.utcnow().isoformat()}Z\n')
        for module in MODULES:
            fh.write(f'Running module: {module}\n')
            fh.flush()
            rc, out = run_script(script, module)
            timestamp = datetime.datetime.utcnow().isoformat() + 'Z'
            fh.write(f'[{timestamp}] module={module} exit={rc}\n')
            fh.write(out + '\n')
            status = 'TEST PASSED' if rc == 0 else 'TEST FAILED'
            fh.write(status + '\n')
            fh.write('---\n')
            if rc != 0:
                overall_success = False

        final = 'TEST PASSED' if overall_success else 'TEST FAILED'
        fh.write(f'Overall result: {final}\n')
    print('Done. Logs saved to', LOG_FILE)
    return 0 if overall_success else 1


if __name__ == '__main__':
    exit(main())
