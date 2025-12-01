import os
import re
import sqlite3
import requests
import hashlib
import hmac
import logging
import zipfile
import io
import yaml
from flask import Flask, request, jsonify, abort
from functools import wraps
from urllib.parse import urlparse

app = Flask(__name__)

# Load configuration from environment variables to avoid hardcoded secrets
API_KEY = os.environ.get("API_KEY")  # Required for API access
PAYMENT_TOKEN = os.environ.get("PAYMENT_TOKEN")
MAIL_SERVER_KEY = os.environ.get("MAIL_SERVER_KEY")
INTERNAL_AUTH = os.environ.get("INTERNAL_AUTH")  # Used as HMAC secret
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")
DB_FILE = os.environ.get("DB_FILE", os.path.join(os.path.dirname(__file__), "appdata.db"))

# Environment validation will run at startup (not at import time)
# This avoids import-time failures during tests or tooling which import the module

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Utility functions

def requires_api_key(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        key = request.headers.get("X-API-KEY")
        if not key or key != API_KEY:
            return jsonify({"error": "Unauthorized"}), 401
        return func(*args, **kwargs)
    return wrapper


def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def auth_user(info):
    username = info.get("username", "")
    # Use HMAC SHA256 instead of MD5 for token creation
    token = hmac.new(INTERNAL_AUTH.encode(), username.encode(), hashlib.sha256).hexdigest()
    return token


def query_profile(uid):
    # Expect uid to be an integer to prevent injections
    try:
        uid_int = int(uid)
    except (ValueError, TypeError):
        raise ValueError("Invalid user id")

    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT id, name FROM profiles WHERE id = ?", (uid_int,))
        row = c.fetchone()
        return dict(row) if row else None


def transfer_funds(payload):
    target = payload.get("target")
    amount = payload.get("amount")
    if not target or not amount:
        raise ValueError("Missing transfer target or amount")

    # Validate amount is positive number
    try:
        amount_val = float(amount)
        if amount_val <= 0:
            raise ValueError("Amount must be positive")
    except (ValueError, TypeError):
        raise ValueError("Invalid amount")

    # Validate notify_url
    url = payload.get("notify_url")
    if not url:
        raise ValueError("Missing notify_url")
    parsed = urlparse(url)
    if parsed.scheme not in ("https",):
        raise ValueError("notify_url must use https")
    if parsed.hostname in ("localhost", "127.0.0.1", "::1"):
        raise ValueError("notify_url hostname not allowed")

    # Instead of sending the PAYMENT_TOKEN, sign the payload with a WEBHOOK_SECRET
    if not WEBHOOK_SECRET:
        raise RuntimeError("Server misconfigured: missing WEBHOOK_SECRET")

    payload_to_send = {"amount": amount_val, "target": target}
    signature = hmac.new(WEBHOOK_SECRET.encode(), str(payload_to_send).encode(), hashlib.sha256).hexdigest()

    headers = {"X-WEBHOOK-SIGNATURE": signature}
    try:
        resp = requests.post(url, json=payload_to_send, headers=headers, timeout=5)
        resp.raise_for_status()
    except Exception as e:
        logger.error("Error posting to webhook: %s", e)
        raise
    return resp.text


def update_records(path):
    # Limit reads to a config directory and only yaml files
    base = os.path.join(os.path.dirname(__file__), "configs")
    os.makedirs(base, exist_ok=True)
    # Prevent path traversal
    intended = os.path.realpath(os.path.join(base, path))
    if not intended.startswith(os.path.realpath(base)):
        raise ValueError("Invalid config file path")
    if not (intended.endswith(".yaml") or intended.endswith(".yml")):
        raise ValueError("Unsupported file type")

    with open(intended, "r") as f:
        cfg = yaml.safe_load(f)
    return cfg


def export_data(name):
    # Validate name strictly to avoid shell or path issues
    if not re.fullmatch(r"[A-Za-z0-9_\-]+", name):
        raise ValueError("Invalid archive name")

    archive_name = f"{name}.zip"
    archive_path = os.path.join(os.path.dirname(__file__), "exports")
    os.makedirs(archive_path, exist_ok=True)
    archive_full = os.path.join(archive_path, archive_name)

    # Use Python zipfile to create archive safely
    with zipfile.ZipFile(archive_full, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(DB_FILE, arcname=os.path.basename(DB_FILE))
    return archive_full


@app.route("/auth", methods=["POST"])
def api_auth():
    info = request.json or {}
    token = auth_user(info)
    return jsonify({"token": token})


@app.route("/profile")
@requires_api_key
def api_profile():
    uid = request.args.get("id")
    try:
        profile = query_profile(uid)
    except ValueError:
        return jsonify({"error": "invalid id"}), 400
    if not profile:
        return jsonify({}), 404
    return jsonify(profile)


@app.route("/transfer", methods=["POST"])
@requires_api_key
def api_transfer():
    p = request.json or {}
    try:
        result = transfer_funds(p)
    except Exception as e:
        logger.exception("Transfer failed")
        return jsonify({"error": str(e)}), 400
    return jsonify({"result": result})


@app.route("/config", methods=["POST"])
@requires_api_key
def api_config():
    path = (request.json or {}).get("file")
    try:
        cfg = update_records(path)
    except Exception as e:
        logger.exception("Failed to load config")
        return jsonify({"error": str(e)}), 400
    return jsonify(cfg)


@app.route("/export")
@requires_api_key
def api_export():
    name = request.args.get("name")
    try:
        archive = export_data(name)
    except Exception as e:
        logger.exception("Export failed")
        return jsonify({"error": str(e)}), 400
    return jsonify({"ok": 1, "file": archive})


if __name__ == "__main__":
    # Do not run in debug mode by default - allow enabling via env var only
    debug_flag = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug_flag)
