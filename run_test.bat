@echo off
REM Run security tests for both backup and patched modules
python -u tests\run_tests.py
IF %ERRORLEVEL% EQU 0 (
    echo TEST PASSED
    exit /b 0
) ELSE (
    echo TEST FAILED
    exit /b 1
)
