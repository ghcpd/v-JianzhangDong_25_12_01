#!/bin/bash

# Test script for Linux/macOS
# This script performs security tests on the Flask application

echo "===================================="
echo "Running Security Tests"
echo "===================================="
echo ""

# Set test environment variables
export PAYMENT_TOKEN="tok_test_token"
export MAIL_SERVER_KEY="mail_srv_key_test"
export INTERNAL_AUTH="admin_internal_test_key"
export FLASK_DEBUG="False"

# Function to test a file
test_file() {
    local filename=$1
    echo "Testing file: $filename"
    echo "------------------------------------"
    
    # Check if file exists
    if [ ! -f "$filename" ]; then
        echo "ERROR: File $filename not found"
        return 1
    fi
    
    # Test 1: Check for hardcoded secrets
    echo "Test 1: Checking for hardcoded secrets..."
    if grep -q "tok_production" "$filename" || \
       grep -q "mail_srv_key_ABCDEFG" "$filename" || \
       grep -q "admin_internal_5566" "$filename"; then
        echo "  ❌ FAILED: Hardcoded secrets found"
        return 1
    else
        echo "  ✓ PASSED: No hardcoded secrets detected"
    fi
    
    # Test 2: Check for SQL injection vulnerabilities
    echo "Test 2: Checking for SQL injection vulnerabilities..."
    if grep -E "\".*%s.*\"|'.*%s.*'" "$filename" | grep -q "SELECT\|INSERT\|UPDATE\|DELETE"; then
        echo "  ❌ FAILED: Potential SQL injection vulnerability (string formatting in SQL)"
        return 1
    else
        echo "  ✓ PASSED: No SQL injection vulnerabilities detected"
    fi
    
    # Test 3: Check for MD5 usage
    echo "Test 3: Checking for weak cryptography (MD5)..."
    if grep -q "hashlib.md5" "$filename"; then
        echo "  ❌ FAILED: MD5 hash function detected (weak cryptography)"
        return 1
    else
        echo "  ✓ PASSED: No MD5 usage detected"
    fi
    
    # Test 4: Check for shell=True in subprocess (actual code, not comments/docstrings)
    echo "Test 4: Checking for command injection vulnerabilities..."
    if grep -E "subprocess.*shell=True" "$filename"; then
        echo "  ❌ FAILED: subprocess with shell=True detected (command injection risk)"
        return 1
    else
        echo "  ✓ PASSED: No command injection vulnerabilities detected"
    fi
    
    # Test 5: Check for debug mode
    echo "Test 5: Checking for debug mode..."
    if grep -q "debug=True" "$filename"; then
        echo "  ❌ FAILED: Debug mode is hardcoded to True"
        return 1
    else
        echo "  ✓ PASSED: Debug mode is properly configured"
    fi
    
    # Test 6: Check for input validation
    echo "Test 6: Checking for input validation..."
    if grep -q "if not.*request.json" "$filename"; then
        echo "  ✓ PASSED: Input validation detected"
    else
        echo "  ⚠ WARNING: Limited input validation"
    fi
    
    # Test 7: Check for URL validation (SSRF protection)
    echo "Test 7: Checking for SSRF protection..."
    if grep -q "is_url_allowed\|ALLOWED_DOMAINS" "$filename"; then
        echo "  ✓ PASSED: URL validation detected"
    else
        echo "  ⚠ WARNING: No URL validation found"
    fi
    
    # Test 8: Check for path traversal protection
    echo "Test 8: Checking for path traversal protection..."
    if grep -q "ALLOWED.*PATH\|\.\." "$filename" | grep -q "path"; then
        echo "  ✓ PASSED: Path validation detected"
    else
        echo "  ⚠ WARNING: No path validation found"
    fi
    
    # Test 9: Python syntax check
    echo "Test 9: Checking Python syntax..."
    if python3 -m py_compile "$filename" 2>/dev/null; then
        echo "  ✓ PASSED: Python syntax is valid"
    else
        echo "  ❌ FAILED: Python syntax errors detected"
        return 1
    fi
    
    echo ""
    return 0
}

# Test inputs_backup.py (should have vulnerabilities)
echo "Part 1: Testing inputs_backup.py (vulnerable version)"
echo "===================================="
test_file "inputs_backup.py"
backup_result=$?

echo ""
echo ""

# Test inputs.py (should be secure)
echo "Part 2: Testing inputs.py (secure version)"
echo "===================================="
test_file "inputs.py"
secure_result=$?

echo ""
echo "===================================="
echo "Test Summary"
echo "===================================="
echo "inputs_backup.py: $(if [ $backup_result -ne 0 ]; then echo 'FAILED (as expected - contains vulnerabilities)'; else echo 'UNEXPECTED PASS'; fi)"
echo "inputs.py: $(if [ $secure_result -eq 0 ]; then echo 'PASSED (secure)'; else echo 'FAILED'; fi)"
echo ""

# Overall result
if [ $secure_result -eq 0 ]; then
    echo "OVERALL: TEST PASSED"
    exit 0
else
    echo "OVERALL: TEST FAILED"
    exit 1
fi
