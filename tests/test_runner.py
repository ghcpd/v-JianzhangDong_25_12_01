import sys
import os
import sqlite3
import importlib
import inspect
import tempfile
import json
from types import SimpleNamespace

# Set up a small test DB and files
TMP_DIR = os.path.join(os.path.dirname(__file__), 'tmp')
os.makedirs(TMP_DIR, exist_ok=True)
DB_PATH = os.path.join(TMP_DIR, 'test.db')

# Create test database
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS profiles (id INTEGER PRIMARY KEY, name TEXT, balance REAL)')
c.execute('DELETE FROM profiles')
c.execute("INSERT INTO profiles (id, name, balance) VALUES (1, 'Alice', 100.0)")
c.execute("INSERT INTO profiles (id, name, balance) VALUES (2, 'Bob', 50.0)")
conn.commit()
conn.close()

# Create a 'configs' directory and a test yaml, and a parent secret file
BASE = os.path.dirname(__file__)
CONFIG_DIR = os.path.join(BASE, 'configs')
os.makedirs(CONFIG_DIR, exist_ok=True)
with open(os.path.join(CONFIG_DIR, 'test.yaml'), 'w', encoding='utf-8') as f:
    f.write('key: value\n')

# Create a sensitive file outside the configs dir to detect path traversal read
PARENT_SECRET = os.path.join(BASE, '..', 'parent_secret.txt')
with open(PARENT_SECRET, 'w', encoding='utf-8') as f:
    f.write('sensitive_data=topsecret')


def run_tests(module_name):
    print('Running tests for', module_name)
    module = importlib.import_module(module_name)

    # Set expected globals for the module
    setattr(module, 'DB_FILE', DB_PATH)
    setattr(module, 'API_KEY', 'TEST_API_KEY')
    setattr(module, 'INTERNAL_AUTH', 'test_internals')
    setattr(module, 'WEBHOOK_SECRET', 'webhook_secret')

    test_failures = []

    # Monkeypatch requests.post to capture arguments
    class DummyResponse:
        def __init__(self):
            self.status_code = 200
            self.text = 'ok'
        def raise_for_status(self):
            return

    posts = []

    def fake_post(url, json=None, headers=None, timeout=None):
        posts.append({'url': url, 'json': json, 'headers': headers})
        return DummyResponse()

    try:
        import requests as real_requests
        real_post = real_requests.post
        real_requests.post = fake_post
    except Exception:
        real_requests = None
        real_post = None

    # Test 1: SQL Injection
    try:
        res = module.query_profile("1' OR '1'='1")
        if isinstance(res, list) and len(res) > 1:
            print('SQL Injection: Vulnerable (returned multiple rows)')
            test_failures.append('sql_injection')
        else:
            print('SQL Injection: Not detected')
    except Exception as e:
        # secure implementation may throw ValueError due to invalid id
        print('SQL Injection: Not detected (exception)', e)

    # Test 2: update_records path traversal
    try:
        # Attempt to read the parent_secret using path traversal
        module.update_records('../parent_secret.txt')
        print('Path traversal in update_records: Vulnerable (read parent secret)')
        test_failures.append('path_traversal')
    except Exception as e:
        print('Path traversal in update_records: Not detected (exception)', e)

    # Test 3: export_data uses subprocess or zipfile
    try:
        src = inspect.getsource(module.export_data)
        if 'subprocess' in src:
            print('export_data: Vulnerable (uses subprocess)')
            test_failures.append('command_injection')
        else:
            print('export_data: Not vulnerable (no subprocess detected)')
    except Exception as e:
        print('export_data source inspection failed', e)

    # Test 4: transfer_funds sends PAYMENT_TOKEN or signed headers
    try:
        payload = {'target': 'acct_test', 'amount': '10', 'notify_url': 'https://example.com/notify'}
        module.transfer_funds(payload)
        if posts:
            post = posts[-1]
            j = post.get('json')
            h = post.get('headers') or {}
            if j and isinstance(j, dict) and 'token' in j:
                print('transfer_funds: Vulnerable (sends token in payload)')
                test_failures.append('token_leak')
            elif h and 'X-WEBHOOK-SIGNATURE' in h:
                print('transfer_funds: Not vulnerable (signed headers used)')
            else:
                print('transfer_funds: Unknown behavior')
        else:
            print('transfer_funds: No HTTP posts detected (likely error)')
    except Exception as e:
        print('transfer_funds: Exception during call', e)

    # Restore requests.post if modified
    if real_requests and real_post:
        real_requests.post = real_post

    if test_failures:
        print('Vulnerabilities detected for', module_name, ':', json.dumps(test_failures))
        return 1
    print('No vulnerabilities detected for', module_name)
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: test_runner.py <module_name>')
        sys.exit(2)
    module_name = sys.argv[1]
    code = run_tests(module_name)
    sys.exit(code)
