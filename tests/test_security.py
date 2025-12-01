import os
import sqlite3
import tempfile
import importlib.util
from pathlib import Path
import unittest
from unittest import mock
import hmac
import hashlib


def load_module(path: str):
    spec = importlib.util.spec_from_file_location("target_module", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore
    return module


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.target_file = os.environ.get("TARGET_FILE", "input.py")
        self.is_backup = "backup" in Path(self.target_file).stem

    def _load(self):
        return load_module(self.target_file)

    def test_query_profile_sql_injection(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            os.environ["DB_FILE"] = str(db_path)
            # Setup DB
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE profiles (id INTEGER PRIMARY KEY, name TEXT, balance REAL)")
            conn.execute("INSERT INTO profiles (id, name, balance) VALUES (1, 'Alice', 100.0)")
            conn.execute("INSERT INTO profiles (id, name, balance) VALUES (2, 'Bob', 200.0)")
            conn.commit()
            conn.close()

            mod = self._load()
            # Ensure backup module points to temp DB (it ignores env)
            try:
                mod.DB_FILE = str(db_path)
            except Exception:
                pass
            payload = "1' OR '1'='1"
            if self.is_backup:
                rows = mod.query_profile(payload)
                # Insecure: returns both rows due to injection
                self.assertEqual(len(rows), 2)
            else:
                with self.assertRaises(ValueError):
                    mod.query_profile(payload)

    @mock.patch("requests.post")
    def test_transfer_funds_ssrf_protection(self, mock_post):
        os.environ["ALLOWED_NOTIFY_HOSTS"] = "localhost"
        mod = self._load()
        payload = {"target": "acct", "amount": 10, "notify_url": "http://evil.com/callback"}
        if self.is_backup:
            # Insecure: performs request to untrusted host
            mod.transfer_funds(payload)
            mock_post.assert_called_once()
            self.assertIn("evil.com", mock_post.call_args[0][0])
        else:
            with self.assertRaises(ValueError):
                mod.transfer_funds(payload)
            mock_post.assert_not_called()

    def test_export_data_command_injection(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "db.sqlite"
            db_path.write_text("dummy")
            os.environ["DB_FILE"] = str(db_path)
            mod = self._load()
            bad_name = "bad;rm -rf x"
            if self.is_backup:
                with mock.patch("subprocess.Popen") as mp:
                    mod.export_data(bad_name)
                    # Command injection risk: name ends up in shell command
                    cmd = mp.call_args[0][0]
                    self.assertIn(bad_name, cmd)
            else:
                with self.assertRaises(ValueError):
                    mod.export_data(bad_name)

    def test_auth_user_hash_strength(self):
        username = "alice"
        if self.is_backup:
            mod = self._load()
            token = mod.auth_user({"username": username})
            self.assertEqual(len(token), 32)  # md5 hex length
        else:
            os.environ["INTERNAL_AUTH_SECRET"] = "secretkey"
            mod = self._load()
            token = mod.auth_user({"username": username})
            expected = hmac.new(b"secretkey", username.encode(), hashlib.sha256).hexdigest()
            self.assertEqual(token, expected)
            self.assertEqual(len(token), 64)

    def test_update_records_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_dir = Path(tmp) / "config"
            cfg_dir.mkdir()
            safe_file = cfg_dir / "cfg.yaml"
            safe_file.write_text("a: 1")
            os.environ["CONFIG_DIR"] = str(cfg_dir)
            mod = self._load()
            if self.is_backup:
                # Insecure: will attempt to open traversal path (FileNotFoundError here)
                with self.assertRaises(FileNotFoundError):
                    mod.update_records("../etc/passwd")
            else:
                with self.assertRaises(ValueError):
                    mod.update_records("../etc/passwd")


if __name__ == "__main__":
    unittest.main()
