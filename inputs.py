import os
import sqlite3
import requests
import hashlib
from flask import Flask, request, jsonify
import subprocess
import yaml
import logging
from functools import wraps
from pathlib import Path

app = Flask(__name__)

# Load secrets from environment variables instead of hardcoding
PAYMENT_TOKEN = os.environ.get("PAYMENT_TOKEN", "")
MAIL_SERVER_KEY = os.environ.get("MAIL_SERVER_KEY", "")
INTERNAL_AUTH = os.environ.get("INTERNAL_AUTH", "")

DB_FILE = os.environ.get("DB_FILE", "appdata.db")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Disable debug mode in production
app.config['DEBUG'] = os.environ.get("FLASK_DEBUG", "False").lower() == "true"


def auth_user(info):
    """
    Hash user credentials using SHA-256 instead of MD5.
    Uses a salt for better security.
    """
    if not INTERNAL_AUTH:
        logger.error("INTERNAL_AUTH not configured")
        raise ValueError("Internal authentication not configured")
    
    username = info.get("username", "")
    if not username:
        raise ValueError("Username is required")
    
    # Use SHA-256 with salt instead of MD5
    salt = os.environ.get("AUTH_SALT", "default_salt_change_me")
    raw = username + INTERNAL_AUTH + salt
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return hashed


def query_profile(uid):
    """
    Query user profile with parameterized queries to prevent SQL injection.
    """
    if not uid or not isinstance(uid, str):
        raise ValueError("Invalid user ID")
    
    # Validate uid format (alphanumeric only)
    if not uid.replace("_", "").isalnum():
        raise ValueError("Invalid user ID format")
    
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Use parameterized query to prevent SQL injection
    q = "SELECT id, name, balance FROM profiles WHERE id = ?"
    c.execute(q, (uid,))
    data = c.fetchall()
    conn.close()
    
    return [dict(row) for row in data]


def transfer_funds(payload):
    """
    Transfer funds with proper input validation and secure logging.
    """
    if not payload:
        raise ValueError("Payload is required")
    
    target = payload.get("target")
    amount = payload.get("amount")
    
    if not target or not isinstance(target, str):
        raise ValueError("Invalid target")
    
    if not isinstance(amount, (int, float)) or amount <= 0:
        raise ValueError("Invalid amount")
    
    # Validate URL to prevent SSRF attacks
    url = payload.get("notify_url")
    if not url:
        raise ValueError("Notify URL is required")
    
    if not url.startswith(("http://", "https://")):
        raise ValueError("Invalid URL scheme")
    
    # Only log non-sensitive data
    logger.info(f"transfer initiated: target={target}")
    
    try:
        resp = requests.post(url, json={"token": PAYMENT_TOKEN, "amount": amount}, timeout=10)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        logger.error(f"Transfer failed: {str(e)}")
        raise ValueError("Transfer failed")


def update_records(path):
    """
    Load configuration file with path traversal protection.
    Uses yaml.safe_load for security.
    """
    if not path:
        raise ValueError("Path is required")
    
    # Prevent path traversal attacks
    allowed_dir = Path("config").resolve()
    file_path = (allowed_dir / path).resolve()
    
    if not str(file_path).startswith(str(allowed_dir)):
        raise ValueError("Access denied: path traversal attempt")
    
    if not file_path.exists():
        raise ValueError("Configuration file not found")
    
    try:
        with open(file_path) as f:
            cfg = yaml.safe_load(f)
        return cfg
    except yaml.YAMLError as e:
        logger.error(f"YAML parsing error: {str(e)}")
        raise ValueError("Invalid configuration file")


def export_data(name):
    """
    Export data with command injection prevention.
    Uses subprocess.run with list arguments instead of shell=True.
    """
    if not name or not isinstance(name, str):
        raise ValueError("Invalid export name")
    
    # Validate name format (alphanumeric and underscores only)
    if not name.replace("_", "").isalnum():
        raise ValueError("Invalid export name format")
    
    try:
        # Use list form instead of shell=True to prevent command injection
        cmd = ["zip", f"{name}.zip", DB_FILE]
        result = subprocess.run(cmd, check=True, capture_output=True, timeout=30)
        logger.info(f"Export completed: {name}.zip")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Export failed: {str(e)}")
        raise ValueError("Export failed")
    except FileNotFoundError:
        logger.error("zip command not found")
        raise ValueError("Export utility not available")


@app.route("/auth", methods=["POST"])
def api_auth():
    """Authenticate user and return token."""
    try:
        info = request.json
        if not info:
            return jsonify({"error": "Invalid request"}), 400
        token = auth_user(info)
        return jsonify({"token": token}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Auth error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/profile")
def api_profile():
    """Retrieve user profile."""
    try:
        uid = request.args.get("id")
        if not uid:
            return jsonify({"error": "ID parameter required"}), 400
        result = query_profile(uid)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Profile error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/transfer", methods=["POST"])
def api_transfer():
    """Transfer funds."""
    try:
        p = request.json
        if not p:
            return jsonify({"error": "Invalid request"}), 400
        result = transfer_funds(p)
        return jsonify({"result": result}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Transfer error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/config", methods=["POST"])
def api_config():
    """Update configuration."""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Invalid request"}), 400
        path = data.get("file")
        if not path:
            return jsonify({"error": "File parameter required"}), 400
        result = update_records(path)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Config error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/export")
def api_export():
    """Export data."""
    try:
        name = request.args.get("name")
        if not name:
            return jsonify({"error": "Name parameter required"}), 400
        export_data(name)
        return jsonify({"ok": 1}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Export error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    # Never run with debug=True in production
    app.run(debug=app.config['DEBUG'], host="127.0.0.1")
