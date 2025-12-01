@echo off
REM Run tests for specified module (backup or fixed)
SET "MODULE=%1"
IF "%MODULE%"=="" SET "MODULE=backup"
SET "MODULE_UNDER_TEST=%MODULE%"
python -m pytest -q tests/test_input.py
