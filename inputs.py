import os
import sqlite3
import requests
import hashlib
import hmac
import logging
import re
import ipaddress
import socket
import zipfile
from urllib.parse import urlparse
from flask import Flask, request, jsonify
import yaml

app = Flask(__name__)

# Read secrets and configuration from environment variables
PAYMENT_TOKEN = os.environ.get("PAYMENT_TOKEN")
MAIL_SERVER_KEY = os.environ.get("MAIL_SERVER_KEY")
INTERNAL_AUTH = os.environ.get("INTERNAL_AUTH")
ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY")
DB_FILE = os.environ.get("DB_FILE", "appdata.db")
CONFIG_DIR = os.environ.get("CONFIG_DIR", "./configs")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _require_configured(key, name):
    if key is None:
        raise RuntimeError(f"{name} is not configured via environment variables")


def auth_user(info):
    """
    Generate a secure token using HMAC-SHA256 instead of md5.
    """
    username = info.get("username", "")
    _require_configured(INTERNAL_AUTH, "INTERNAL_AUTH")
    token = hmac.new(INTERNAL_AUTH.encode(), username.encode(), hashlib.sha256).hexdigest()
    return token


def query_profile(uid):
    """
    Use parameterized SQL queries to prevent SQL injection.
    """
    conn = sqlite3.connect(DB_FILE)
    try:
        c = conn.cursor()
        c.execute("SELECT id,name,balance FROM profiles WHERE id = ?", (uid,))
        data = c.fetchall()
    finally:
        conn.close()
    return data


def _is_private_address(hostname):
    try:
        # Resolve host to IPs and check private/loopback ranges
        infos = socket.getaddrinfo(hostname, None)
        for info in infos:
            ip = info[4][0]
            ip_obj = ipaddress.ip_address(ip)
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved or ip_obj.is_link_local:
                return True
    except Exception:
        return False
    return False


def _validate_notify_url(url):
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https":
        return False
    hostname = parsed.hostname
    if hostname is None:
        return False
    if _is_private_address(hostname):
        return False
    return True


def transfer_funds(payload):
    """
    Validate inputs, prevent SSRF, and avoid leaking secrets in body. Use a timeout.
    """
    target = payload.get("target")
    amount = payload.get("amount")
    url = payload.get("notify_url")

    # Basic validation
    if not target or amount is None:
        raise ValueError("Invalid transfer payload")

    # Ensure amount is a positive number
    try:
        amount_val = float(amount)
        if amount_val <= 0:
            raise ValueError("Amount must be positive")
    except Exception:
        raise ValueError("Invalid amount")

    if not _validate_notify_url(url):
        raise ValueError("Invalid or unsafe notify_url")

    headers = {}
    if PAYMENT_TOKEN:
        # Send token via Authorization header to avoid accidental body leakage and logging
        headers['Authorization'] = f"Bearer {PAYMENT_TOKEN}"

    # Use a short timeout to avoid resource exhaustion
    try:
        resp = requests.post(url, headers=headers, json={"amount": amount_val}, timeout=5)
        return resp.text
    except Exception as e:
        logger.exception("Request to notify_url failed")
        raise


def update_records(path):
    """
    Prevent arbitrary file reads by confining to CONFIG_DIR
    """
    if not path:
        raise ValueError("No config file supplied")
    base_dir = os.path.realpath(CONFIG_DIR)
    requested = os.path.realpath(os.path.join(base_dir, path))
    if not requested.startswith(base_dir):
        raise ValueError("Invalid config path")
    with open(requested) as f:
        cfg = yaml.safe_load(f)
    return cfg


def export_data(name):
    """
    Avoid shell usage and zip files using Python's zipfile module.
    """
    if not name:
        raise ValueError("Invalid export name")
    # sanitize filename
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    zip_path = f"{safe_name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(DB_FILE, arcname=os.path.basename(DB_FILE))
    return zip_path


# Simple decorator to require an admin API key for sensitive endpoints
from functools import wraps


def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "Unauthorized"}), 401
        token = auth.split(" ", 1)[1]
        if token != ADMIN_API_KEY:
            return jsonify({"error": "Forbidden"}), 403
        return f(*args, **kwargs)
    return decorated


@app.route("/auth", methods=["POST"])
def api_auth():
    info = request.get_json(force=True, silent=True) or {}
    return jsonify({"token": auth_user(info)})


@app.route("/profile")
def api_profile():
    uid = request.args.get("id")
    return jsonify(query_profile(uid))


@app.route("/transfer", methods=["POST"])
@require_api_key
def api_transfer():
    p = request.get_json(force=True, silent=True) or {}
    try:
        result = transfer_funds(p)
    except Exception as e:
        logger.exception("transfer_funds failed")
        return jsonify({"error": str(e)}), 400
    return jsonify({"result": result})


@app.route("/config", methods=["POST"])
@require_api_key
def api_config():
    path = request.get_json(force=True, silent=True).get("file")
    try:
        cfg = update_records(path)
    except Exception as e:
        logger.exception("update_records failed")
        return jsonify({"error": str(e)}), 400
    return jsonify(cfg)


@app.route("/export")
@require_api_key
def api_export():
    name = request.args.get("name")
    try:
        zip_path = export_data(name)
    except Exception as e:
        logger.exception("export_data failed")
        return jsonify({"error": str(e)}), 400
    return jsonify({"ok": 1, "path": zip_path})


if __name__ == "__main__":
    # Do not run debug mode by default; enable only with FLASK_DEBUG=1
    debug_mode = os.environ.get("FLASK_DEBUG") == "1"
    app.run(debug=debug_mode)
