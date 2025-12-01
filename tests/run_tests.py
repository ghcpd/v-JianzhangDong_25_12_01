import os
import sys
import importlib.machinery
import importlib.util
import sqlite3
import json

# Setup small test DB and files
TEST_DB = os.path.abspath("test_appdata.db")
SECRETS_FILE = os.path.abspath("secrets.txt")


def prepare_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    conn = sqlite3.connect(TEST_DB)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS profiles (id TEXT PRIMARY KEY, name TEXT, balance REAL)")
    c.execute("INSERT INTO profiles (id, name, balance) VALUES (?, ?, ?)", ("1", "Alice", 100.0))
    c.execute("INSERT INTO profiles (id, name, balance) VALUES (?, ?, ?)", ("2", "Bob", 50.0))
    conn.commit()
    conn.close()


def prepare_files():
    with open(SECRETS_FILE, "w") as f:
        f.write("top_secret=42")


def load_module(path, name):
    """Dynamically import a module from a path"""
    loader = importlib.machinery.SourceFileLoader(name, path)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def run_checks(module):
    results = {}

    # SQL Injection check
    try:
        res = module.query_profile("1' OR '1'='1")
        results['sql_injection_returned_multiple'] = len(res) > 1
    except Exception as e:
        results['sql_injection_error'] = str(e)

    # File traversal check
    try:
        # read parent secrets (path traversal)
        module.CONFIG_DIR = os.path.abspath('.')  # set base dir to current for test
        res = module.update_records("../secrets.txt")
        results['file_traversal_read'] = True
    except Exception as e:
        results['file_traversal_read'] = False

    # Command injection check: monkeypatch subprocess.Popen if exists
    try:
        import subprocess as std_sub
        called = {'cmd': None}

        def fake_popen(cmd, shell=False, *args, **kwargs):
            called['cmd'] = (cmd, shell)
            class Fake:
                def __init__(self):
                    self.pid = 1234
            return Fake()

        if hasattr(module, 'subprocess'):
            module.subprocess.Popen_backup = module.subprocess.Popen
            module.subprocess.Popen = fake_popen
            try:
                module.export_data("evil; rm -rf /")
            except Exception:
                pass
            module.subprocess.Popen = module.subprocess.Popen_backup
            results['command_injection_possible'] = called['cmd'] is not None and called['cmd'][1] == True
        else:
            # If module doesn't import subprocess, then likely secure (using zipfile)
            try:
                result_path = module.export_data("evil; rm -rf /")
                results['command_injection_possible'] = False
            except Exception:
                results['command_injection_possible'] = False
    except Exception as e:
        results['command_injection_error'] = str(e)

    # SSRF check: monkeypatch requests.post
    try:
        called = {'url': None}
        def fake_post(url, *args, **kwargs):
            called['url'] = url
            class FakeResp:
                status_code = 200
                text = 'ok'
            return FakeResp()

        if hasattr(module, 'requests'):
            module.requests_post_backup = module.requests.post
            module.requests.post = fake_post
            try:
                module.transfer_funds({'target': '1', 'amount': 1, 'notify_url': 'http://127.0.0.1/notify'})
            except Exception:
                pass
            module.requests.post = module.requests_post_backup
            results['ssrf_allowed'] = called['url'] is not None
        else:
            results['ssrf_allowed'] = False
    except Exception as e:
        results['ssrf_error'] = str(e)

    # Hash function check (md5 vs hmac-sha256): check length
    try:
        token = module.auth_user({'username': 'user'})
        results['auth_token_length'] = len(token)
    except Exception as e:
        results['auth_token_error'] = str(e)

    return results


def main():
    prepare_db()
    prepare_files()

    modules = [
        ("input_backup.py", 'backup', True),
        ("inputs.py", 'patched', False),
    ]

    overall_pass = True
    full_report = {}

    for mod_path, mod_name, expect_vulnerable in modules:
        os.environ['DB_FILE'] = TEST_DB
        # ensure config dir is the current tests folder
        os.environ['CONFIG_DIR'] = os.path.abspath('.')
        # set admin api key for patched module
        os.environ['ADMIN_API_KEY'] = 'adminkey123'
        # reload module
        mod = load_module(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', mod_path)), mod_name)
        results = run_checks(mod)
        # Determine vulnerability count: true flags count
        vuln_score = 0
        vuln_score += 1 if results.get('sql_injection_returned_multiple') else 0
        vuln_score += 1 if results.get('file_traversal_read') else 0
        vuln_score += 1 if results.get('command_injection_possible') else 0
        vuln_score += 1 if results.get('ssrf_allowed') else 0
        # md5 token length 32 => vulnerable; 64 => secure
        token_len = results.get('auth_token_length') or 0
        if token_len == 32:
            vuln_score += 1

        module_pass = True
        if expect_vulnerable:
            module_pass = vuln_score > 0
        else:
            module_pass = vuln_score == 0

        full_report[mod_name] = {
            'results': results,
            'vuln_score': vuln_score,
            'passed': module_pass
        }
        overall_pass = overall_pass and module_pass

    # Save report
    with open('tests_report.json', 'w') as f:
        json.dump(full_report, f, indent=2)

    # Exit 0 if all modules met expectations, else 1
    if overall_pass:
        print('TESTS COMPLETED: all expectations met')
        sys.exit(0)
    else:
        print('TESTS FAILED: expectations not met')
        sys.exit(2)


if __name__ == '__main__':
    main()
