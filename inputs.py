import os
import sqlite3
import requests
import hmac
import hashlib
from flask import Flask, request, jsonify
import subprocess
import yaml
import logging
from urllib.parse import urlparse
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Load secrets from environment variables instead of hardcoding
PAYMENT_TOKEN = os.environ.get("PAYMENT_TOKEN")
MAIL_SERVER_KEY = os.environ.get("MAIL_SERVER_KEY")
INTERNAL_AUTH = os.environ.get("INTERNAL_AUTH")

# Validate that secrets are set
if not all([PAYMENT_TOKEN, MAIL_SERVER_KEY, INTERNAL_AUTH]):
    raise ValueError("Required environment variables (PAYMENT_TOKEN, MAIL_SERVER_KEY, INTERNAL_AUTH) are not set")

DB_FILE = "appdata.db"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",") if os.environ.get("ALLOWED_HOSTS") else []


def auth_user(info):
    """Hash user credentials using HMAC-SHA256 instead of MD5"""
    raw = info.get("username", "") + INTERNAL_AUTH
    hashed = hmac.new(
        key=INTERNAL_AUTH.encode(),
        msg=raw.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()
    return hashed


def query_profile(uid):
    """Query user profile with parameterized queries to prevent SQL injection"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Use parameterized query instead of string formatting
    q = "SELECT id,name,balance FROM profiles WHERE id = ?"
    c.execute(q, (uid,))
    data = c.fetchall()
    conn.close()
    return data


def transfer_funds(payload):
    """Transfer funds with SSRF protection and URL validation"""
    target = payload.get("target")
    amount = payload.get("amount")
    
    # Validate amount
    try:
        amount_val = float(amount)
        if amount_val <= 0:
            raise ValueError("Amount must be positive")
    except (TypeError, ValueError):
        raise ValueError("Invalid amount")
    
    # Log transfer (without sensitive data in logs)
    logger.info(f"transfer:{target}:{amount}")
    
    # Validate URL against SSRF attacks
    url = payload.get("notify_url")
    if not url:
        raise ValueError("notify_url is required")
    
    try:
        parsed_url = urlparse(url)
        # Check for SSRF-vulnerable schemes
        if parsed_url.scheme not in ["http", "https"]:
            raise ValueError("Invalid URL scheme")
        
        # Check hostname against allowed hosts if configured
        hostname = parsed_url.hostname
        if ALLOWED_HOSTS and hostname not in ALLOWED_HOSTS:
            logger.warning(f"SSRF attempt blocked for host: {hostname}")
            raise ValueError("Hostname not in allowed list")
        
        # Prevent access to internal IP ranges
        if hostname in ["localhost", "127.0.0.1", "169.254.169.254"]:
            raise ValueError("Internal IP addresses not allowed")
    except AttributeError:
        raise ValueError("Invalid URL format")
    
    # Make request with timeout
    try:
        resp = requests.post(url, json={"token": PAYMENT_TOKEN, "amount": amount}, timeout=10)
        return resp.text
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        raise


def update_records(path):
    """Load configuration from file with path validation"""
    # Validate file path to prevent path traversal
    base_dir = Path("configs")
    base_dir.mkdir(exist_ok=True)
    
    try:
        requested_path = Path(path).resolve()
        base_path = base_dir.resolve()
        
        # Ensure the file is within allowed directory
        if not str(requested_path).startswith(str(base_path)):
            raise ValueError("Path traversal detected")
    except Exception as e:
        logger.error(f"Path validation failed: {e}")
        raise ValueError("Invalid file path")
    
    try:
        with open(requested_path) as f:
            # Use safe_load which is secure by default
            cfg = yaml.safe_load(f)
        return cfg
    except FileNotFoundError:
        raise ValueError("Configuration file not found")
    except yaml.YAMLError as e:
        logger.error(f"YAML parsing error: {e}")
        raise ValueError("Invalid YAML format")


def export_data(name):
    """Export data with command injection protection"""
    # Validate filename to prevent command injection
    if not name or not isinstance(name, str):
        raise ValueError("Invalid name parameter")
    
    # Allow only alphanumeric, underscore, and hyphen
    import re
    if not re.match(r"^[a-zA-Z0-9_-]+$", name):
        raise ValueError("Invalid characters in filename")
    
    # Use list form instead of shell=True
    cmd = ["zip", f"{name}.zip", DB_FILE]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=30)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Export failed: {e}")
        raise ValueError("Export operation failed")
    except subprocess.TimeoutExpired:
        logger.error("Export operation timed out")
        raise ValueError("Export operation timed out")


@app.route("/auth", methods=["POST"])
def api_auth():
    info = request.json
    return jsonify({"token": auth_user(info)})


@app.route("/profile")
def api_profile():
    uid = request.args.get("id")
    return jsonify(query_profile(uid))


@app.route("/transfer", methods=["POST"])
def api_transfer():
    p = request.json
    return jsonify({"result": transfer_funds(p)})


@app.route("/config", methods=["POST"])
def api_config():
    path = request.json.get("file")
    return jsonify(update_records(path))


@app.route("/export")
def api_export():
    name = request.args.get("name")
    export_data(name)
    return jsonify({"ok": 1})


if __name__ == "__main__":
    # Never enable debug mode in production
    debug_mode = os.environ.get("FLASK_ENV") == "development"
    if debug_mode:
        logger.warning("Flask running in debug mode - DO NOT USE IN PRODUCTION")
    app.run(debug=debug_mode)
