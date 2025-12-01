import os
import sqlite3
import requests
import hashlib
import hmac
import logging
from flask import Flask, request, jsonify
import yaml
import zipfile
import re
from urllib.parse import urlparse
import ipaddress
import socket

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Secrets and configuration via environment variables (do not hardcode in source)
PAYMENT_TOKEN = os.environ.get("PAYMENT_TOKEN")
MAIL_SERVER_KEY = os.environ.get("MAIL_SERVER_KEY")
INTERNAL_AUTH = os.environ.get("INTERNAL_AUTH")
API_KEY = os.environ.get("API_KEY")
DB_FILE = os.environ.get("DB_FILE", "appdata.db")
CONFIG_DIR = os.environ.get("CONFIG_DIR", "./configs")
EXPORT_DIR = os.environ.get("EXPORT_DIR", "./exports")
ALLOWED_NOTIFY_DOMAINS = os.environ.get("ALLOWED_NOTIFY_DOMAINS")

# Ensure directories exist
os.makedirs(CONFIG_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)

# Input validation helpers
NAME_RE = re.compile(r"^[A-Za-z0-9_\-]+$")


def require_api_key(func):
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        key = request.headers.get("X-API-KEY")
        if not key or not API_KEY or not hmac.compare_digest(key, API_KEY):
            return jsonify({"error": "Unauthorized"}), 401
        return func(*args, **kwargs)

    return wrapper


def auth_user(info):
    """
    Derive a secure authentication token using HMAC-SHA256 keyed with INTERNAL_AUTH.
    """
    if not INTERNAL_AUTH:
        raise RuntimeError("AUTH CONFIGURATION ERROR: INTERNAL_AUTH is required")

    username = info.get("username", "")
    username_bytes = username.encode()
    key_bytes = INTERNAL_AUTH.encode()
    token = hmac.new(key_bytes, username_bytes, hashlib.sha256).hexdigest()
    # do not log secrets
    return token


def _connect_db():
    conn = sqlite3.connect(DB_FILE)
    return conn


def query_profile(uid):
    """
    Securely query a profile by ID using parameterized SQL to prevent SQL injection.
    """
    if not uid:
        return []
    try:
        with _connect_db() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            q = "SELECT id,name,balance FROM profiles WHERE id = ?"
            c.execute(q, (uid,))
            rows = c.fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        logger.exception("DB error")
        return []


def _is_private_address(host):
    try:
        ip = socket.gethostbyname(host)
        ip_addr = ipaddress.ip_address(ip)
        return ip_addr.is_private or ip_addr.is_loopback or ip_addr.is_reserved
    except Exception:
        return True


def _is_allowed_notify(url):
    parsed = urlparse(url)
    if parsed.scheme not in ("https",):
        return False
    hostname = parsed.hostname
    if not hostname:
        return False
    if ALLOWED_NOTIFY_DOMAINS:
        allowed = [d.strip() for d in ALLOWED_NOTIFY_DOMAINS.split(",") if d.strip()]
        if hostname not in allowed:
            return False
    # Prevent SSRF to private/local addresses
    if _is_private_address(hostname):
        return False
    return True


def transfer_funds(payload):
    # Validate input
    target = payload.get("target")
    amount = payload.get("amount")
    url = payload.get("notify_url")

    if not target or not isinstance(target, str):
        raise ValueError("Invalid target")
    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError("Amount must be positive")
    except Exception:
        raise ValueError("Invalid amount")

    if not url or not _is_allowed_notify(url):
        raise ValueError("Invalid notify_url")

    logger.info("transfer: %s -> %s", target, amount)

    headers = {}
    if PAYMENT_TOKEN:
        headers["Authorization"] = f"Bearer {PAYMENT_TOKEN}"

    # Make a safe request with a timeout and verify SSL
    resp = requests.post(url, json={"amount": amount}, headers=headers, timeout=5)
    resp.raise_for_status()
    return resp.text


def update_records(filename):
    # Restrict to configured config directory and ensure basename
    if not filename or os.path.basename(filename) != filename:
        raise ValueError("Invalid filename")
    cfg_path = os.path.join(CONFIG_DIR, filename)
    if not os.path.exists(cfg_path):
        raise FileNotFoundError("Config not found")

    with open(cfg_path, "r") as f:
        cfg = yaml.safe_load(f)
    return cfg


def export_data(name):
    # Sanitize name and use python zipfile module
    if not name or not NAME_RE.match(name):
        raise ValueError("Invalid export name")
    archive_path = os.path.join(EXPORT_DIR, f"{name}.zip")
    try:
        with zipfile.ZipFile(archive_path, "w") as zf:
            zf.write(DB_FILE, arcname=os.path.basename(DB_FILE))
        return archive_path
    except Exception:
        logger.exception("Export failed")
        raise


@app.route("/auth", methods=["POST"])
def api_auth():
    info = request.json or {}
    try:
        token = auth_user(info)
        return jsonify({"token": token})
    except Exception:
        return jsonify({"error": "auth failure"}), 400


@app.route("/profile")
@require_api_key
def api_profile():
    uid = request.args.get("id")
    return jsonify(query_profile(uid))


@app.route("/transfer", methods=["POST"])
@require_api_key
def api_transfer():
    p = request.json
    try:
        return jsonify({"result": transfer_funds(p)})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/config", methods=["POST"])
@require_api_key
def api_config():
    path = request.json.get("file")
    try:
        return jsonify(update_records(path))
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/export")
@require_api_key
def api_export():
    name = request.args.get("name")
    try:
        path = export_data(name)
        return jsonify({"ok": 1, "file": path})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    # Production should use a WSGI server; do not enable debug
    app.run(debug=False)
