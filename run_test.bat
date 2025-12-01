@echo off
SET MODULE=%1
IF "%MODULE%"=="" SET MODULE=inputs
python -m tests.test_runner %MODULE%
EXIT /B %ERRORLEVEL%
