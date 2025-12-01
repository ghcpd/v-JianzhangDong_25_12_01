@echo off
setlocal
set "TARGET_FILE=%TARGET_FILE%"
if "%TARGET_FILE%"=="" set "TARGET_FILE=input.py"
python -m unittest tests.test_security
set "EXITCODE=%ERRORLEVEL%"
endlocal & exit /b %EXITCODE%
