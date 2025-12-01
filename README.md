# Security Audit Report: inputs.py

## Executive Summary

This document provides a comprehensive security audit of the `inputs.py` application. A total of **8 critical security vulnerabilities** have been identified and fixed:

- **3 Critical Vulnerabilities**: SQL Injection, Command Injection, Hardcoded Secrets
- **3 High Severity Vulnerabilities**: Weak Cryptographic Hash, SSRF, Path Traversal
- **2 Medium Severity Vulnerabilities**: Insecure Flask Debug Mode, Missing Input Validation

All vulnerabilities have been remediated in the secured version of the code.

---

## Generated Files Overview

### Core Application Files
- **`inputs_backup.py`** - Original vulnerable version (for comparison and testing)
- **`inputs.py`** - Secured version with all vulnerabilities fixed
- **`report.json`** - Detailed vulnerability report in JSON format with severity levels

### Environment and Dependencies
- **`requirements.txt`** - Python package dependencies
- **`Dockerfile`** - Docker containerization for consistent deployment
- **`setup.sh`** - Environment setup script for Linux/macOS
- **`.dockerenv`** - Marker file for Docker environment detection

### Testing and Validation
- **`run_test.sh`** - Test script for Linux/macOS environments
- **`run_test.bat`** - Test script for Windows environments
- **`auto_test.py`** - Automatic test execution with environment detection
- **`test_runner.py`** - (Auto-generated) Vulnerability detection test suite

### Documentation
- **`README.md`** - This file

### Logs Directory
- **`logs/test_run.log`** - Comprehensive test execution log

---

## Vulnerability Summary

### 1. SQL Injection (Critical) - Line 27
**Location**: `query_profile()` function

**Vulnerability**: SQL query constructed using string formatting with user input.
```python
# VULNERABLE
q = "SELECT id,name,balance FROM profiles WHERE id = '%s'" % uid
```

**Fix**: Use parameterized queries
```python
# SECURE
q = "SELECT id,name,balance FROM profiles WHERE id = ?"
c.execute(q, (uid,))
```

---

### 2. Command Injection (Critical) - Line 48
**Location**: `export_data()` function

**Vulnerability**: Command constructed with user input and executed with `shell=True`.
```python
# VULNERABLE
cmd = f"zip {name}.zip {DB_FILE}"
subprocess.Popen(cmd, shell=True)
```

**Fix**: Use subprocess with list argument and input validation
```python
# SECURE
import re
if not re.match(r"^[a-zA-Z0-9_-]+$", name):
    raise ValueError("Invalid characters in filename")
cmd = ["zip", f"{name}.zip", DB_FILE]
subprocess.run(cmd, check=True, capture_output=True, timeout=30)
```

---

### 3. Hardcoded Secrets (Critical) - Lines 12-14
**Location**: Module-level constants

**Vulnerability**: Sensitive credentials hardcoded in source code.
```python
# VULNERABLE
PAYMENT_TOKEN = "tok_production_998877"
MAIL_SERVER_KEY = "mail_srv_key_ABCDEFG"
INTERNAL_AUTH = "admin_internal_5566"
```

**Fix**: Load from environment variables
```python
# SECURE
PAYMENT_TOKEN = os.environ.get("PAYMENT_TOKEN")
MAIL_SERVER_KEY = os.environ.get("MAIL_SERVER_KEY")
INTERNAL_AUTH = os.environ.get("INTERNAL_AUTH")

if not all([PAYMENT_TOKEN, MAIL_SERVER_KEY, INTERNAL_AUTH]):
    raise ValueError("Required environment variables are not set")
```

---

### 4. Weak Cryptographic Hash (High) - Line 21
**Location**: `auth_user()` function

**Vulnerability**: MD5 hashing is cryptographically broken and not suitable for security purposes.
```python
# VULNERABLE
hashed = hashlib.md5(raw.encode()).hexdigest()
```

**Fix**: Use HMAC-SHA256
```python
# SECURE
import hmac
hashed = hmac.new(
    key=INTERNAL_AUTH.encode(),
    msg=raw.encode(),
    digestmod=hashlib.sha256
).hexdigest()
```

---

### 5. Server-Side Request Forgery - SSRF (High) - Lines 39-41
**Location**: `transfer_funds()` function

**Vulnerability**: User-controlled URL used directly in HTTP request without validation.
```python
# VULNERABLE
url = payload.get("notify_url")
resp = requests.post(url, json={"token": PAYMENT_TOKEN, "amount": amount})
```

**Fix**: Comprehensive URL validation
```python
# SECURE
from urllib.parse import urlparse

url = payload.get("notify_url")
parsed_url = urlparse(url)

# Scheme validation
if parsed_url.scheme not in ["http", "https"]:
    raise ValueError("Invalid URL scheme")

# Internal IP prevention
if parsed_url.hostname in ["localhost", "127.0.0.1", "169.254.169.254"]:
    raise ValueError("Internal IP addresses not allowed")

# Allowlist check (if configured)
if ALLOWED_HOSTS and parsed_url.hostname not in ALLOWED_HOSTS:
    raise ValueError("Hostname not in allowed list")

# Timeout protection
resp = requests.post(url, json={...}, timeout=10)
```

---

### 6. Path Traversal (High) - Line 36
**Location**: `update_records()` function

**Vulnerability**: File path used directly without validation, allowing `../` traversal.
```python
# VULNERABLE
def update_records(path):
    with open(path) as f:
        cfg = yaml.safe_load(f)
```

**Fix**: Path validation and restriction to config directory
```python
# SECURE
from pathlib import Path

def update_records(path):
    base_dir = Path("configs")
    base_dir.mkdir(exist_ok=True)
    
    requested_path = Path(path).resolve()
    base_path = base_dir.resolve()
    
    if not str(requested_path).startswith(str(base_path)):
        raise ValueError("Path traversal detected")
    
    with open(requested_path) as f:
        cfg = yaml.safe_load(f)
```

---

### 7. Insecure Flask Debug Mode (Medium) - Line 82
**Location**: Application startup

**Vulnerability**: Debug mode enabled in production exposes sensitive information.
```python
# VULNERABLE
if __name__ == "__main__":
    app.run(debug=True)
```

**Fix**: Environment-based debug mode
```python
# SECURE
if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_ENV") == "development"
    if debug_mode:
        logger.warning("Flask running in debug mode - DO NOT USE IN PRODUCTION")
    app.run(debug=debug_mode)
```

---

### 8. Missing Input Validation (Medium) - Lines 35-41
**Location**: Multiple endpoints and functions

**Vulnerability**: User input not validated for type, format, or reasonable values.

**Fix**: Comprehensive validation
```python
# SECURE
try:
    amount_val = float(amount)
    if amount_val <= 0:
        raise ValueError("Amount must be positive")
except (TypeError, ValueError):
    raise ValueError("Invalid amount")

# Add logging instead of print
logger.info(f"transfer:{target}:{amount}")
```

---

## Setup Instructions

### Prerequisites
- Python 3.8 or higher
- Git (for cloning the repository)
- pip (Python package manager)
- Docker (optional, for containerized deployment)

### Option 1: Linux/macOS Setup

#### Step 1: Clone and navigate to the project
```bash
cd /path/to/project
```

#### Step 2: Run setup script
```bash
chmod +x setup.sh
./setup.sh
```

#### Step 3: Set environment variables
```bash
# Create a .env file or set variables in your shell
export PAYMENT_TOKEN="your_actual_payment_token"
export MAIL_SERVER_KEY="your_actual_mail_key"
export INTERNAL_AUTH="your_actual_internal_auth"
export FLASK_ENV="production"  # Set to "development" only for testing
export ALLOWED_HOSTS="api.example.com,webhook.example.com"  # Comma-separated
```

#### Step 4: Activate virtual environment
```bash
source venv/bin/activate
```

#### Step 5: Install dependencies
```bash
pip install -r requirements.txt
```

---

### Option 2: Windows Setup

#### Step 1: Clone and navigate to the project
```powershell
cd C:\path\to\project
```

#### Step 2: Create virtual environment
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

#### Step 3: Install dependencies
```powershell
pip install -r requirements.txt
```

#### Step 4: Set environment variables
```powershell
# Set for current session
$env:PAYMENT_TOKEN = "your_actual_payment_token"
$env:MAIL_SERVER_KEY = "your_actual_mail_key"
$env:INTERNAL_AUTH = "your_actual_internal_auth"
$env:FLASK_ENV = "production"
$env:ALLOWED_HOSTS = "api.example.com,webhook.example.com"

# For permanent settings, use System Settings or create a .env file
```

#### Step 5: Create necessary directories
```powershell
mkdir configs
mkdir logs
```

---

### Option 3: Docker Setup

#### Step 1: Build the Docker image
```bash
docker build -t secure-inputs:latest .
```

#### Step 2: Run the container
```bash
docker run \
  -e PAYMENT_TOKEN="your_actual_payment_token" \
  -e MAIL_SERVER_KEY="your_actual_mail_key" \
  -e INTERNAL_AUTH="your_actual_internal_auth" \
  -e FLASK_ENV="production" \
  -e ALLOWED_HOSTS="api.example.com,webhook.example.com" \
  -p 5000:5000 \
  -v $(pwd)/configs:/app/configs \
  -v $(pwd)/logs:/app/logs \
  secure-inputs:latest
```

---

## Running Tests

### Linux/macOS Test Execution

#### Quick Test Run
```bash
source venv/bin/activate
./run_test.sh
```

#### With Auto-Detection
```bash
source venv/bin/activate
python3 auto_test.py
```

---

### Windows Test Execution

#### Quick Test Run
```powershell
venv\Scripts\Activate.ps1
.\run_test.bat
```

#### With Auto-Detection
```powershell
venv\Scripts\Activate.ps1
python auto_test.py
```

---

### Docker Test Execution

```bash
docker run \
  -v $(pwd):/app \
  -w /app \
  -e PAYMENT_TOKEN="test_token" \
  -e MAIL_SERVER_KEY="test_key" \
  -e INTERNAL_AUTH="test_auth" \
  secure-inputs:latest \
  python auto_test.py
```

---

## Understanding Test Scripts

### run_test.sh (Linux/macOS)
- **Purpose**: Validates security fixes by comparing vulnerable and secure versions
- **Function**: Checks for presence of vulnerabilities in `inputs_backup.py` and absence in `inputs.py`
- **Checks**:
  - SQL Injection patterns
  - Hardcoded secrets
  - Command injection vulnerabilities
  - Weak cryptographic hashing
  - SSRF vulnerabilities
  - Debug mode status
  - Path traversal vulnerabilities

### run_test.bat (Windows)
- **Purpose**: Windows equivalent of run_test.sh
- **Function**: Same vulnerability detection as Linux version
- **Output**: Creates test_runner.py and executes it

### auto_test.py
- **Purpose**: Automatic environment detection and test execution
- **Features**:
  - Detects OS (Windows/Linux/macOS)
  - Detects Docker environment
  - Creates necessary directories
  - Generates test configuration
  - Logs all output to `logs/test_run.log`
  - Includes timestamp in logs
  - Reports final status: `TEST PASSED` or `TEST FAILED`

---

## Checking Logs and Test Results

### Log File Location
```
logs/test_run.log
```

### Viewing Logs on Linux/macOS
```bash
# View entire log
cat logs/test_run.log

# View last 50 lines
tail -50 logs/test_run.log

# Follow log in real-time
tail -f logs/test_run.log

# Search for specific content
grep "TEST PASSED\|TEST FAILED" logs/test_run.log
```

### Viewing Logs on Windows
```powershell
# View entire log
Get-Content logs/test_run.log

# View last 50 lines
Get-Content logs/test_run.log -Tail 50

# Search for specific content
Select-String "TEST PASSED|TEST FAILED" logs/test_run.log
```

### Log Format Example
```
2025-12-01 10:30:45,123 - INFO - ============================================================
2025-12-01 10:30:45,124 - INFO - Security Audit Auto Test Script
2025-12-01 10:30:45,125 - INFO - Start Time: 2025-12-01 10:30:45
2025-12-01 10:30:45,126 - INFO - ============================================================
2025-12-01 10:30:45,127 - INFO - Environment detected: windows
...
2025-12-01 10:30:47,890 - INFO - ============================================================
2025-12-01 10:30:47,891 - INFO - FINAL STATUS: TEST PASSED
2025-12-01 10:30:47,892 - INFO - All security vulnerabilities have been identified and fixed.
2025-12-01 10:30:47,893 - INFO - End Time: 2025-12-01 10:30:47
2025-12-01 10:30:47,894 - INFO - ============================================================
```

### Test Status Interpretation

#### TEST PASSED
- **Meaning**: All vulnerabilities were successfully identified and fixed
- **Requirements Met**:
  1. Vulnerabilities present in `inputs_backup.py`
  2. Same vulnerabilities absent in `inputs.py`
  3. All security patches applied correctly

#### TEST FAILED
- **Meaning**: One or more issues detected
- **Possible Reasons**:
  1. Vulnerabilities not found in backup (file may be incomplete)
  2. Vulnerabilities still exist in secured version (fixes not applied)
  3. Test execution error (missing dependencies, file access issues)

---

## Detailed Vulnerability Report

For comprehensive vulnerability information, review:
```bash
# View the JSON report
cat report.json

# Pretty-print the JSON report (Linux/macOS)
python3 -m json.tool report.json

# Pretty-print the JSON report (Windows)
python -m json.tool report.json
```

### Report Structure
The `report.json` contains:
- **summary**: Statistics on vulnerability counts by severity
- **details**: Array of vulnerability objects, each containing:
  - Vulnerability ID
  - File and line numbers affected
  - Vulnerability type and severity
  - Description of the issue
  - Explanation of the fix
  - Secure code snippet for reference

---

## Security Best Practices Applied

1. **Input Validation**: All user inputs validated for type, format, and value ranges
2. **Parameterized Queries**: SQL queries use parameter binding, not string formatting
3. **Secret Management**: Sensitive data loaded from environment variables, never hardcoded
4. **Secure Cryptography**: HMAC-SHA256 replaces MD5; strong algorithms preferred
5. **SSRF Protection**: URL validation with scheme, hostname, and timeout checks
6. **Command Safety**: Subprocess calls use list arguments, never shell=True
7. **Path Validation**: File access restricted to designated directories
8. **Error Handling**: Graceful error handling without exposing sensitive information
9. **Logging**: Structured logging replaces print statements; no sensitive data logged
10. **Environment Configuration**: Production security settings controlled via environment

---

## Deployment Checklist

Before deploying to production:

- [ ] Set all required environment variables (PAYMENT_TOKEN, MAIL_SERVER_KEY, INTERNAL_AUTH)
- [ ] Configure ALLOWED_HOSTS with actual webhook hostnames
- [ ] Set FLASK_ENV to "production" (not "development")
- [ ] Run security tests: `python auto_test.py`
- [ ] Verify TEST PASSED status in logs
- [ ] Review logs for any error messages
- [ ] Enable HTTPS for all endpoints
- [ ] Configure proper database access controls
- [ ] Implement rate limiting
- [ ] Set up monitoring and alerting
- [ ] Review and update security patches regularly

---

## Troubleshooting

### Issue: "Python not found"
**Solution**: 
- Linux/macOS: Install Python 3 via `apt-get install python3` or `brew install python3`
- Windows: Download from https://www.python.org/downloads/

### Issue: "Module not found" errors
**Solution**: 
```bash
# Linux/macOS
source venv/bin/activate
pip install -r requirements.txt

# Windows
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Issue: "Environment variables not set"
**Solution**: Verify environment variables before running:
```bash
# Linux/macOS
echo $PAYMENT_TOKEN
echo $MAIL_SERVER_KEY
echo $INTERNAL_AUTH

# Windows
$env:PAYMENT_TOKEN
$env:MAIL_SERVER_KEY
$env:INTERNAL_AUTH
```

### Issue: "Permission denied" on setup.sh
**Solution**: Make script executable
```bash
chmod +x setup.sh
chmod +x run_test.sh
./setup.sh
```

### Issue: "TEST FAILED" status
**Solution**: 
1. Check logs: `cat logs/test_run.log`
2. Verify file integrity: `ls -la inputs.py inputs_backup.py`
3. Re-run tests with verbose output
4. Check for syntax errors: `python3 -m py_compile inputs.py`

---

## Additional Resources

### Security References
- OWASP Top 10: https://owasp.org/www-project-top-ten/
- CWE (Common Weakness Enumeration): https://cwe.mitre.org/
- NIST Secure Coding Standards: https://www.nist.gov/

### Flask Security
- Flask Documentation: https://flask.palletsprojects.com/
- Flask Security Best Practices: https://flask.palletsprojects.com/security/

### Python Security
- Python Security Best Practices: https://python.readthedocs.io/
- OWASP Python Security: https://owasp.org/www-community/Python

---

## Support and Questions

For questions about specific vulnerabilities or fixes, refer to:
1. **report.json** - Detailed technical information
2. **inputs_backup.py** vs **inputs.py** - Side-by-side comparison
3. **This README** - Comprehensive documentation

---

## Conclusion

All identified vulnerabilities in `inputs.py` have been successfully remediated. The secure version implements industry-standard security practices and is ready for production deployment with proper environment configuration. Regular security reviews and updates are recommended.

**Security Audit Status**: ✓ COMPLETE  
**Vulnerability Fixes**: ✓ APPLIED  
**Testing**: ✓ AUTOMATED  
**Documentation**: ✓ COMPREHENSIVE

---

*Generated: 2025-12-01*  
*Audit Scope: inputs.py*  
*Total Vulnerabilities Fixed: 8*
