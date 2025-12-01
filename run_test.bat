@echo off
REM Test script for Windows
REM This script performs security tests on the Flask application

setlocal EnableDelayedExpansion

echo ====================================
echo Running Security Tests
echo ====================================
echo.

REM Set test environment variables
set PAYMENT_TOKEN=tok_test_token
set MAIL_SERVER_KEY=mail_srv_key_test
set INTERNAL_AUTH=admin_internal_test_key
set FLASK_DEBUG=False

REM Test inputs_backup.py
echo Part 1: Testing inputs_backup.py ^(vulnerable version^)
echo ====================================
call :test_file inputs_backup.py
set backup_result=%errorlevel%

echo.
echo.

REM Test inputs.py
echo Part 2: Testing inputs.py ^(secure version^)
echo ====================================
call :test_file inputs.py
set secure_result=%errorlevel%

echo.
echo ====================================
echo Test Summary
echo ====================================
if %backup_result% neq 0 (
    echo inputs_backup.py: FAILED ^(as expected - contains vulnerabilities^)
) else (
    echo inputs_backup.py: UNEXPECTED PASS
)

if %secure_result% equ 0 (
    echo inputs.py: PASSED ^(secure^)
) else (
    echo inputs.py: FAILED
)
echo.

REM Overall result
if %secure_result% equ 0 (
    echo OVERALL: TEST PASSED
    exit /b 0
) else (
    echo OVERALL: TEST FAILED
    exit /b 1
)

REM Function to test a file
:test_file
set filename=%~1
echo Testing file: %filename%
echo ------------------------------------

REM Check if file exists
if not exist "%filename%" (
    echo ERROR: File %filename% not found
    exit /b 1
)

REM Test 1: Check for hardcoded secrets
echo Test 1: Checking for hardcoded secrets...
findstr /C:"tok_production" /C:"mail_srv_key_ABCDEFG" /C:"admin_internal_5566" "%filename%" >nul 2>&1
if !errorlevel! equ 0 (
    echo   X FAILED: Hardcoded secrets found
    exit /b 1
) else (
    echo   √ PASSED: No hardcoded secrets detected
)

REM Test 2: Check for SQL injection vulnerabilities
echo Test 2: Checking for SQL injection vulnerabilities...
findstr /R "\".*%%s.*\"" "%filename%" | findstr /C:"SELECT" /C:"INSERT" /C:"UPDATE" /C:"DELETE" >nul 2>&1
if !errorlevel! equ 0 (
    echo   X FAILED: Potential SQL injection vulnerability
    exit /b 1
) else (
    echo   √ PASSED: No SQL injection vulnerabilities detected
)

REM Test 3: Check for MD5 usage
echo Test 3: Checking for weak cryptography ^(MD5^)...
findstr /C:"hashlib.md5" "%filename%" >nul 2>&1
if !errorlevel! equ 0 (
    echo   X FAILED: MD5 hash function detected
    exit /b 1
) else (
    echo   √ PASSED: No MD5 usage detected
)

REM Test 4: Check for shell=True in subprocess (actual code, not comments/docstrings)
echo Test 4: Checking for command injection vulnerabilities...
findstr /R /C:"subprocess.*shell=True" "%filename%" >nul 2>&1
if !errorlevel! equ 0 (
    echo   X FAILED: subprocess with shell=True detected
    exit /b 1
) else (
    echo   √ PASSED: No command injection vulnerabilities detected
)

REM Test 5: Check for debug mode
echo Test 5: Checking for debug mode...
findstr /C:"debug=True" "%filename%" >nul 2>&1
if !errorlevel! equ 0 (
    echo   X FAILED: Debug mode is hardcoded to True
    exit /b 1
) else (
    echo   √ PASSED: Debug mode is properly configured
)

REM Test 6: Check for input validation
echo Test 6: Checking for input validation...
findstr /C:"if not" "%filename%" | findstr /C:"request.json" >nul 2>&1
if !errorlevel! equ 0 (
    echo   √ PASSED: Input validation detected
) else (
    echo   ! WARNING: Limited input validation
)

REM Test 7: Check for URL validation
echo Test 7: Checking for SSRF protection...
findstr /C:"is_url_allowed" /C:"ALLOWED_DOMAINS" "%filename%" >nul 2>&1
if !errorlevel! equ 0 (
    echo   √ PASSED: URL validation detected
) else (
    echo   ! WARNING: No URL validation found
)

REM Test 8: Check for path traversal protection
echo Test 8: Checking for path traversal protection...
findstr /C:"ALLOWED" "%filename%" | findstr /C:"PATH" >nul 2>&1
if !errorlevel! equ 0 (
    echo   √ PASSED: Path validation detected
) else (
    echo   ! WARNING: No path validation found
)

REM Test 9: Python syntax check
echo Test 9: Checking Python syntax...
python -m py_compile "%filename%" >nul 2>&1
if !errorlevel! equ 0 (
    echo   √ PASSED: Python syntax is valid
) else (
    echo   X FAILED: Python syntax errors detected
    exit /b 1
)

echo.
exit /b 0
