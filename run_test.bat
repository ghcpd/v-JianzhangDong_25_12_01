@echo off
REM Test script for Windows
REM Tests the security audit fixes

setlocal enabledelayedexpansion

echo ==========================================
echo Running Security Audit Tests
echo ==========================================
echo.

REM Create test configuration file
if not exist configs mkdir configs
(
echo database: appdata.db
echo debug: false
echo timeout: 30
) > configs\test_config.yaml

REM Create test runner script
(
echo import sys
echo import re
echo.
echo def check_sql_injection(filename):
echo     """Check if SQL injection vulnerabilities exist"""
echo     with open(filename, 'r') as f:
echo         content = f.read()
echo     
echo     if re.search(r"['\"].*%%\s*\w+.*WHERE", content) or re.search(r"f\".*%%\s*\w+", content):
echo         return True
echo     return False
echo.
echo def check_hardcoded_secrets(filename):
echo     """Check for hardcoded secrets"""
echo     with open(filename, 'r') as f:
echo         content = f.read()
echo     
echo     if re.search(r"PAYMENT_TOKEN\s*=\s*['\"]", content):
echo         return True
echo     if re.search(r"MAIL_SERVER_KEY\s*=\s*['\"]", content):
echo         return True
echo     if re.search(r"INTERNAL_AUTH\s*=\s*['\"]", content):
echo         return True
echo     return False
echo.
echo def check_command_injection(filename):
echo     """Check for command injection vulnerabilities"""
echo     with open(filename, 'r') as f:
echo         content = f.read()
echo     
echo     if re.search(r"subprocess\.(Popen^|call^|run).*shell\s*=\s*True", content):
echo         return True
echo     return False
echo.
echo def check_weak_hash(filename):
echo     """Check for weak cryptographic hashing"""
echo     with open(filename, 'r') as f:
echo         content = f.read()
echo     
echo     if "hashlib.md5" in content:
echo         return True
echo     return False
echo.
echo def check_ssrf(filename):
echo     """Check for SSRF vulnerabilities"""
echo     with open(filename, 'r') as f:
echo         content = f.read()
echo     
echo     if "requests.post(url" in content and "urlparse" not in content:
echo         return True
echo     return False
echo.
echo def check_debug_mode(filename):
echo     """Check for debug mode enabled in production"""
echo     with open(filename, 'r') as f:
echo         content = f.read()
echo     
echo     if re.search(r"app\.run\(debug\s*=\s*True\)", content):
echo         return True
echo     return False
echo.
echo print("=" * 50^)
echo print("INPUTS_BACKUP.PY (VULNERABLE VERSION)^)
echo print("=" * 50^)
echo.
echo backup_file = "inputs_backup.py"
echo has_vuln = False
echo.
echo if check_sql_injection(backup_file^):
echo     print("X SQL Injection Vulnerability: FOUND^)
echo     has_vuln = True
echo else:
echo     print("✓ SQL Injection Vulnerability: NOT FOUND^)
echo.
echo if check_hardcoded_secrets(backup_file^):
echo     print("X Hardcoded Secrets: FOUND^)
echo     has_vuln = True
echo else:
echo     print("✓ Hardcoded Secrets: NOT FOUND^)
echo.
echo if check_command_injection(backup_file^):
echo     print("X Command Injection Vulnerability: FOUND^)
echo     has_vuln = True
echo else:
echo     print("✓ Command Injection Vulnerability: NOT FOUND^)
echo.
echo if check_weak_hash(backup_file^):
echo     print("X Weak Cryptographic Hash ^(MD5^): FOUND^)
echo     has_vuln = True
echo else:
echo     print("✓ Weak Cryptographic Hash: NOT FOUND^)
echo.
echo if check_ssrf(backup_file^):
echo     print("X SSRF Vulnerability: FOUND^)
echo     has_vuln = True
echo else:
echo     print("✓ SSRF Vulnerability: NOT FOUND^)
echo.
echo if check_debug_mode(backup_file^):
echo     print("X Debug Mode Enabled: FOUND^)
echo     has_vuln = True
echo else:
echo     print("✓ Debug Mode Enabled: NOT FOUND^)
echo.
echo print("")
echo print("=" * 50^)
echo print("INPUTS.PY ^(SECURED VERSION^)^)
echo print("=" * 50^)
echo.
echo secure_file = "inputs.py"
echo all_fixed = True
echo.
echo if check_sql_injection(secure_file^):
echo     print("X SQL Injection Vulnerability: STILL EXISTS^)
echo     all_fixed = False
echo else:
echo     print("✓ SQL Injection Vulnerability: FIXED^)
echo.
echo if check_hardcoded_secrets(secure_file^):
echo     print("X Hardcoded Secrets: STILL EXISTS^)
echo     all_fixed = False
echo else:
echo     print("✓ Hardcoded Secrets: FIXED^)
echo.
echo if check_command_injection(secure_file^):
echo     print("X Command Injection Vulnerability: STILL EXISTS^)
echo     all_fixed = False
echo else:
echo     print("✓ Command Injection Vulnerability: FIXED^)
echo.
echo if check_weak_hash(secure_file^):
echo     print("X Weak Cryptographic Hash: STILL EXISTS^)
echo     all_fixed = False
echo else:
echo     print("✓ Weak Cryptographic Hash: FIXED^)
echo.
echo if check_ssrf(secure_file^):
echo     print("X SSRF Vulnerability: STILL EXISTS^)
echo     all_fixed = False
echo else:
echo     print("✓ SSRF Vulnerability: FIXED^)
echo.
echo if check_debug_mode(secure_file^):
echo     print("X Debug Mode Enabled: STILL EXISTS^)
echo     all_fixed = False
echo else:
echo     print("✓ Debug Mode Enabled: FIXED^)
echo.
echo print("")
echo print("=" * 50^)
echo.
echo if has_vuln and all_fixed:
echo     print("TEST RESULT: PASSED^)
echo     print("Vulnerabilities found in backup, all fixed in secured version^)
echo     sys.exit^(0^)
echo else:
echo     print("TEST RESULT: FAILED^)
echo     if not has_vuln:
echo         print("No vulnerabilities detected in backup file^)
echo     if not all_fixed:
echo         print("Some vulnerabilities remain in secured version^)
echo     sys.exit^(1^)
) > test_runner.py

python test_runner.py
set TEST_RESULT=%ERRORLEVEL%

echo.
echo ==========================================
if %TEST_RESULT% equ 0 (
    echo All tests PASSED!
) else (
    echo Some tests FAILED!
)
echo ==========================================

exit /b %TEST_RESULT%
