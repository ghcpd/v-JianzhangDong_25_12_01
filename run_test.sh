#!/bin/bash

# Test script for Linux/macOS
# Tests the security audit fixes

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "Running Security Audit Tests"
echo "=========================================="
echo ""

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Create test configuration file
mkdir -p configs
cat > configs/test_config.yaml << 'EOF'
database: appdata.db
debug: false
timeout: 30
EOF

# Test 1: SQL Injection Check (inputs_backup.py should be vulnerable)
echo "[TEST 1] SQL Injection Vulnerability Check"
echo "Testing inputs_backup.py for SQL injection vulnerability..."

# Create a test Python script to check for SQL injection vulnerabilities
cat > test_runner.py << 'EOF'
import sys
import re

def check_sql_injection(filename):
    """Check if SQL injection vulnerabilities exist"""
    with open(filename, 'r') as f:
        content = f.read()
    
    # Check for vulnerable pattern: string formatting in SQL queries
    if re.search(r"['\"].*%\s*\w+.*WHERE", content) or re.search(r"f\".*%\s*\w+", content):
        return True
    return False

def check_hardcoded_secrets(filename):
    """Check for hardcoded secrets"""
    with open(filename, 'r') as f:
        content = f.read()
    
    # Check for hardcoded tokens and keys
    if re.search(r"PAYMENT_TOKEN\s*=\s*['\"]", content):
        return True
    if re.search(r"MAIL_SERVER_KEY\s*=\s*['\"]", content):
        return True
    if re.search(r"INTERNAL_AUTH\s*=\s*['\"]", content):
        return True
    return False

def check_command_injection(filename):
    """Check for command injection vulnerabilities"""
    with open(filename, 'r') as f:
        content = f.read()
    
    # Check for shell=True with user input
    if re.search(r"subprocess\.(Popen|call|run).*shell\s*=\s*True", content):
        return True
    return False

def check_weak_hash(filename):
    """Check for weak cryptographic hashing"""
    with open(filename, 'r') as f:
        content = f.read()
    
    if "hashlib.md5" in content:
        return True
    return False

def check_ssrf(filename):
    """Check for SSRF vulnerabilities"""
    with open(filename, 'r') as f:
        content = f.read()
    
    # Check for unvalidated URL usage
    if "requests.post(url" in content and "urlparse" not in content:
        return True
    return False

def check_debug_mode(filename):
    """Check for debug mode enabled in production"""
    with open(filename, 'r') as f:
        content = f.read()
    
    if re.search(r"app\.run\(debug\s*=\s*True\)", content):
        return True
    return False

# Check both files
print("=" * 50)
print("INPUTS_BACKUP.PY (VULNERABLE VERSION)")
print("=" * 50)

backup_file = "inputs_backup.py"
has_vuln = False

if check_sql_injection(backup_file):
    print("✗ SQL Injection Vulnerability: FOUND")
    has_vuln = True
else:
    print("✓ SQL Injection Vulnerability: NOT FOUND")

if check_hardcoded_secrets(backup_file):
    print("✗ Hardcoded Secrets: FOUND")
    has_vuln = True
else:
    print("✓ Hardcoded Secrets: NOT FOUND")

if check_command_injection(backup_file):
    print("✗ Command Injection Vulnerability: FOUND")
    has_vuln = True
else:
    print("✓ Command Injection Vulnerability: NOT FOUND")

if check_weak_hash(backup_file):
    print("✗ Weak Cryptographic Hash (MD5): FOUND")
    has_vuln = True
else:
    print("✓ Weak Cryptographic Hash: NOT FOUND")

if check_ssrf(backup_file):
    print("✗ SSRF Vulnerability: FOUND")
    has_vuln = True
else:
    print("✓ SSRF Vulnerability: NOT FOUND")

if check_debug_mode(backup_file):
    print("✗ Debug Mode Enabled: FOUND")
    has_vuln = True
else:
    print("✓ Debug Mode Enabled: NOT FOUND")

print("")
print("=" * 50)
print("INPUTS.PY (SECURED VERSION)")
print("=" * 50)

secure_file = "inputs.py"
all_fixed = True

if check_sql_injection(secure_file):
    print("✗ SQL Injection Vulnerability: STILL EXISTS")
    all_fixed = False
else:
    print("✓ SQL Injection Vulnerability: FIXED")

if check_hardcoded_secrets(secure_file):
    print("✗ Hardcoded Secrets: STILL EXISTS")
    all_fixed = False
else:
    print("✓ Hardcoded Secrets: FIXED")

if check_command_injection(secure_file):
    print("✗ Command Injection Vulnerability: STILL EXISTS")
    all_fixed = False
else:
    print("✓ Command Injection Vulnerability: FIXED")

if check_weak_hash(secure_file):
    print("✗ Weak Cryptographic Hash: STILL EXISTS")
    all_fixed = False
else:
    print("✓ Weak Cryptographic Hash: FIXED")

if check_ssrf(secure_file):
    print("✗ SSRF Vulnerability: STILL EXISTS")
    all_fixed = False
else:
    print("✓ SSRF Vulnerability: FIXED")

if check_debug_mode(secure_file):
    print("✗ Debug Mode Enabled: STILL EXISTS")
    all_fixed = False
else:
    print("✓ Debug Mode Enabled: FIXED")

print("")
print("=" * 50)

if has_vuln and all_fixed:
    print("TEST RESULT: PASSED")
    print("Vulnerabilities found in backup, all fixed in secured version")
    sys.exit(0)
else:
    print("TEST RESULT: FAILED")
    if not has_vuln:
        print("No vulnerabilities detected in backup file")
    if not all_fixed:
        print("Some vulnerabilities remain in secured version")
    sys.exit(1)
EOF

python test_runner.py
TEST_RESULT=$?

echo ""
echo "=========================================="
if [ $TEST_RESULT -eq 0 ]; then
    echo "All tests PASSED!"
else
    echo "Some tests FAILED!"
fi
echo "=========================================="

exit $TEST_RESULT
