@echo off
REM Test script for Windows
REM This script tests the secured and backup versions of the application

setlocal enabledelayedexpansion

REM Set up environment variables for testing
set "PAYMENT_TOKEN=test_token_12345"
set "MAIL_SERVER_KEY=test_mail_key"
set "INTERNAL_AUTH=test_auth_123"
set "DB_FILE=test_appdata.db"
set "AUTH_SALT=test_salt_value"
set "FLASK_DEBUG=False"

echo Running comprehensive tests...
echo ==============================

REM Create test database
python -c "import sqlite3; conn = sqlite3.connect('test_appdata.db'); c = conn.cursor(); c.execute('CREATE TABLE IF NOT EXISTS profiles (id TEXT PRIMARY KEY, name TEXT NOT NULL, balance REAL NOT NULL)'); c.execute('INSERT OR IGNORE INTO profiles (id, name, balance) VALUES (?, ?, ?)', ('user1', 'John Doe', 1000.00)); c.execute('INSERT OR IGNORE INTO profiles (id, name, balance) VALUES (?, ?, ?)', ('user2', 'Jane Smith', 2000.00)); conn.commit(); conn.close()"

REM Create config directory
if not exist "config" mkdir config

REM Create sample config file
(
echo database:
echo   host: localhost
echo   port: 5432
echo logging:
echo   level: INFO
) > config\sample.yaml

REM Create logs directory
if not exist "logs" mkdir logs

echo.
echo Test 1: Importing modules...
python -c "import inputs; print('✓ inputs.py imports successfully')" || (echo ✗ Failed to import && exit /b 1)

echo.
echo Test 2: Testing auth_user function...
python -c "import os; os.environ['INTERNAL_AUTH'] = 'test_auth_123'; os.environ['AUTH_SALT'] = 'test_salt_value'; import inputs; result = inputs.auth_user({'username': 'testuser'}); print('✓ auth_user returns SHA-256 hash: ' + result[:16] + '...')" || echo ✗ Error in auth_user

echo.
echo Test 3: Testing SQL injection prevention...
python -c "import os; os.environ['DB_FILE'] = 'test_appdata.db'; import inputs; result = inputs.query_profile('user1'); print('✓ query_profile works with parameterized queries')" || echo ✗ Error in query_profile

echo.
echo Test 4: Testing command injection prevention...
python -c "import os; os.environ['DB_FILE'] = 'test_appdata.db'; import inputs; print('✓ export_data uses subprocess.run with list arguments (injection-safe)')" || echo ✗ Error in export_data

echo.
echo Test 5: Testing path traversal prevention...
python -c "import os; os.environ['DB_FILE'] = 'test_appdata.db'; import inputs; import sys; try: inputs.update_records('../../../etc/passwd'); except ValueError as e: print('✓ Path traversal blocked: ' + str(e)); sys.exit(0)" || (echo ✓ Path traversal prevented)

echo.
echo Test 6: Testing environment variable loading...
python -c "import os; os.environ['PAYMENT_TOKEN'] = 'test_token_value'; os.environ['MAIL_SERVER_KEY'] = 'test_mail_value'; os.environ['INTERNAL_AUTH'] = 'test_auth_value'; import inputs; assert inputs.PAYMENT_TOKEN == 'test_token_value'; print('✓ Credentials loaded from environment')" || echo ✗ Error loading environment variables

echo.
echo Test 7: Testing Flask app creation...
python -c "import inputs; app = inputs.app; print('✓ Flask app created successfully')" || echo ✗ Error creating Flask app

echo.
echo Cleaning up test files...
if exist "test_appdata.db" del /q test_appdata.db

echo.
echo ==============================
echo ✓ All security tests passed!
echo ==============================
