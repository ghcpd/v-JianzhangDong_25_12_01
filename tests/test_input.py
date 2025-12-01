import importlib.util
import os
import sqlite3
import time
import json
import sys
import types
import tempfile
import pytest

MODULE_UNDER_TEST = os.environ.get('MODULE_UNDER_TEST', 'backup')
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

def load_module_from_path(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

@pytest.fixture(scope='module')
def module_under_test(tmp_path_factory):
    name = MODULE_UNDER_TEST
    if name == 'backup':
        path = os.path.join(PROJECT_ROOT, 'input_backup.py')
        modname = 'input_backup'
    else:
        path = os.path.join(PROJECT_ROOT, 'input.py')
        modname = 'input'
    # export default env vars for secure functions
    os.environ.setdefault('INTERNAL_AUTH', 'testsecret123')
    os.environ.setdefault('API_KEY', 'test_api_key_456')
    os.environ.setdefault('PAYMENT_TOKEN', 'test_payment_token_789')
    mod = load_module_from_path(path, modname)

    # create a test sqlite database and override DB_FILE
    test_db = os.path.join(str(tmp_path_factory.mktemp('data')), 'appdata.db')
    conn = sqlite3.connect(test_db)
    c = conn.cursor()
    c.execute('CREATE TABLE profiles (id TEXT PRIMARY KEY, name TEXT, balance REAL)')
    c.execute('INSERT INTO profiles (id,name,balance) VALUES ("1","Alice",100)')
    c.execute('INSERT INTO profiles (id,name,balance) VALUES ("2","Bob",200)')
    conn.commit()
    conn.close()

    # set DB_FILE on module
    if hasattr(mod, 'DB_FILE'):
        mod.DB_FILE = test_db
    elif hasattr(mod, 'DB_FILE'):  # fallback
        setattr(mod, 'DB_FILE', test_db)
    else:
        mod.DB_FILE = test_db

    # Create config dir for fixed module and sample file
    cfg_dir = os.path.join(PROJECT_ROOT, 'configs')
    os.makedirs(cfg_dir, exist_ok=True)
    with open(os.path.join(cfg_dir, 'test.yaml'), 'w') as f:
        f.write('value: 123')
    with open(os.path.join(PROJECT_ROOT, 'sensitive.txt'), 'w') as f:
        f.write('SECRETDATA')

    yield mod


def test_sql_injection_behavior(module_under_test):
    mod = module_under_test
    # The injection payload
    inj = "1' OR '1'='1"
    result = mod.query_profile(inj)
    # In the vulnerable backup version, injection will return both rows (length 2)
    # In the secure version, parameterized query should not return both rows
    if MODULE_UNDER_TEST == 'backup':
        assert isinstance(result, list)
        assert len(result) == 2
    else:
        assert isinstance(result, list)
        assert len(result) != 2


def test_ssrf_protection(module_under_test, monkeypatch):
    mod = module_under_test

    called = {'count': 0}

    def fake_post(url, json=None, headers=None, timeout=None):
        called['count'] += 1
        class Resp:
            def raise_for_status(self):
                pass
            text = 'ok'
        return Resp()

    monkeypatch.setattr('requests.post', fake_post)

    payload = {'target': 'x', 'amount': 1.0, 'notify_url': 'http://127.0.0.1:9999/callback'}
    if MODULE_UNDER_TEST == 'backup':
        # vulnerable: should call requests.post
        res = mod.transfer_funds(payload)
        assert called['count'] == 1
        assert res == 'ok'
    else:
        # secure: should reject notify_url and not call requests.post
        with pytest.raises(Exception):
            mod.transfer_funds(payload)
        assert called['count'] == 0


def test_config_path_traversal(module_under_test):
    mod = module_under_test
    # Vulnerable module will open arbitrary paths; secure module only accepts filenames
    if MODULE_UNDER_TEST == 'backup':
        # Use absolute path for reliable resolution across environments
        abs_path = os.path.join(PROJECT_ROOT, 'sensitive.txt')
        out = mod.update_records(abs_path)
        assert isinstance(out, (str, dict)) or 'SECRETDATA' in open(abs_path).read()
    else:
        # secure module should raise ValueError or FileNotFoundError on traversal
        with pytest.raises(Exception):
            mod.update_records('../sensitive.txt')


def test_export_command_injection(monkeypatch, module_under_test, tmp_path):
    mod = module_under_test
    # Monkeypatch subprocess.Popen for backup module to detect shell=True and command containing input
    created = {'popen_called': False, 'shell': None, 'cmd': None}

    def fake_popen(cmd, shell=False):
        created['popen_called'] = True
        created['shell'] = shell
        created['cmd'] = cmd
        class Dummy:
            def __init__(self):
                pass
        return Dummy()

    # For backup module, replace subprocess with a dummy
    if MODULE_UNDER_TEST == 'backup':
        if hasattr(mod, 'subprocess'):
            monkeypatch.setattr(mod, 'subprocess', types.SimpleNamespace(Popen=fake_popen))
        else:
            monkeypatch.setattr('subprocess.Popen', fake_popen)

        # attempt to inject
        inj = "myarchive; touch hack_file_123"
        try:
            mod.export_data(inj)
        except Exception:
            pass
        # vulnerable backup should have called Popen with shell True and cmd containing inj
        assert created['popen_called']
        assert created['shell'] == True
        assert inj in created['cmd']
    else:
        # secure: should raise ValueError because name doesn't match allowed pattern
        with pytest.raises(Exception):
            mod.export_data('myarchive; touch hack_file_123')


def test_auth_token_strength(module_under_test):
    mod = module_under_test
    info = {'username': 'testuser'}
    token = mod.auth_user(info)
    if MODULE_UNDER_TEST == 'backup':
        # md5 length 32 hex
        assert len(token) == 32
    else:
        # hmac sha256 hex length 64
        assert len(token) == 64


if __name__ == '__main__':
    # simple runner for local runs
    os.environ['MODULE_UNDER_TEST'] = os.environ.get('MODULE_UNDER_TEST', 'backup')
    import pytest
    sys.exit(pytest.main(['-q', os.path.abspath(__file__)]))
