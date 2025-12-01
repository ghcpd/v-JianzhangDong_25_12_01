#!/usr/bin/env python3

"""
Auto Test Script for Security Audit
Detects environment, runs tests, and logs results
"""

import os
import sys
import platform
import subprocess
import logging
from datetime import datetime
from pathlib import Path

# Setup logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "test_run.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def detect_environment():
    """Detect the current environment"""
    system = platform.system()
    logger.info(f"Detected OS: {system}")
    
    # Check if running in Docker
    if os.path.exists("/.dockerenv"):
        return "docker"
    
    if system == "Windows":
        return "windows"
    elif system in ["Linux", "Darwin"]:
        return "linux"
    else:
        return "unknown"


def create_test_runner():
    """Create the test runner script"""
    test_code = r'''import sys
import re

def check_sql_injection(filename):
    """Check if SQL injection vulnerabilities exist"""
    with open(filename, 'r') as f:
        content = f.read()
    
    # Check for vulnerable pattern: string formatting in SQL queries
    if '%s' in content and 'WHERE' in content and 'c.execute(q)' in content and 'c.execute(q, (' not in content:
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
        lines = f.readlines()
    
    # Check for shell=True with user input (skip comments)
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        if "shell=True" in line and "subprocess" in line:
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
    
    # Check for unvalidated URL usage in requests
    if 'requests.post(url' in content and 'urlparse' not in content:
        return True
    return False

def check_debug_mode(filename):
    """Check for debug mode enabled in production"""
    with open(filename, 'r') as f:
        content = f.read()
    
    # Look for debug=True without environment check
    if 'app.run(debug=True)' in content:
        return True
    return False

def check_path_traversal(filename):
    """Check for path traversal vulnerabilities"""
    with open(filename, 'r') as f:
        content = f.read()
    
    # Check if open() is called with user input without validation
    if 'open(path)' in content and 'Path(path).resolve()' not in content:
        return True
    return False

# Check both files
backup_file = "inputs_backup.py"
secure_file = "inputs.py"

checks = {
    "SQL Injection": check_sql_injection,
    "Hardcoded Secrets": check_hardcoded_secrets,
    "Command Injection": check_command_injection,
    "Weak Hash (MD5)": check_weak_hash,
    "SSRF": check_ssrf,
    "Debug Mode": check_debug_mode,
    "Path Traversal": check_path_traversal,
}

all_tests_passed = True

for check_name, check_func in checks.items():
    backup_has_vuln = check_func(backup_file)
    secure_has_vuln = check_func(secure_file)
    
    if not backup_has_vuln:
        print(f"ERROR: {check_name} not found in backup file")
        all_tests_passed = False
    
    if secure_has_vuln:
        print(f"ERROR: {check_name} still exists in secure file")
        all_tests_passed = False

sys.exit(0 if all_tests_passed else 1)
'''
    return test_code


def run_test_windows():
    """Run tests on Windows"""
    logger.info("=" * 60)
    logger.info("TESTING INPUTS_BACKUP.PY (VULNERABLE VERSION)")
    logger.info("=" * 60)
    
    test_code = create_test_runner()
    
    try:
        result = subprocess.run(
            [sys.executable, "-c", test_code],
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        
        if result.stdout:
            logger.info(result.stdout)
        if result.stderr:
            logger.error(result.stderr)
        
        if result.returncode == 0:
            logger.info("TEST PASSED")
            return True
        else:
            logger.error("TEST FAILED")
            return False
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        return False


def run_test_linux():
    """Run tests on Linux/macOS"""
    logger.info("=" * 60)
    logger.info("TESTING INPUTS_BACKUP.PY (VULNERABLE VERSION)")
    logger.info("=" * 60)
    
    # Create test runner script
    test_script = Path("test_runner.py")
    test_code = create_test_runner()
    
    try:
        test_script.write_text(test_code)
        
        result = subprocess.run(
            [sys.executable, str(test_script)],
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        
        if result.stdout:
            logger.info(result.stdout)
        if result.stderr:
            logger.error(result.stderr)
        
        if result.returncode == 0:
            logger.info("TEST PASSED")
            return True
        else:
            logger.error("TEST FAILED")
            return False
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        return False
    finally:
        # Cleanup
        if test_script.exists():
            test_script.unlink()


def run_test_docker():
    """Run tests in Docker"""
    logger.info("=" * 60)
    logger.info("Running tests in Docker environment")
    logger.info("=" * 60)
    
    test_code = create_test_runner()
    
    try:
        result = subprocess.run(
            [sys.executable, "-c", test_code],
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        
        if result.stdout:
            logger.info(result.stdout)
        if result.stderr:
            logger.error(result.stderr)
        
        if result.returncode == 0:
            logger.info("TEST PASSED")
            return True
        else:
            logger.error("TEST FAILED")
            return False
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        return False


def main():
    """Main test execution function"""
    logger.info("=" * 60)
    logger.info("Security Audit Auto Test Script")
    logger.info(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    logger.info("")
    
    # Detect environment
    env = detect_environment()
    logger.info(f"Environment detected: {env}")
    logger.info("")
    
    # Ensure configs and logs directories exist
    Path("configs").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    
    # Create test config file
    config_file = Path("configs/test_config.yaml")
    config_file.write_text("""database: appdata.db
debug: false
timeout: 30
""")
    
    all_tests_passed = True
    
    # Run tests based on environment
    if env == "windows":
        passed = run_test_windows()
    elif env in ["linux", "docker"]:
        passed = run_test_linux()
    else:
        logger.error(f"Unknown environment: {env}")
        passed = False
    
    all_tests_passed = all_tests_passed and passed
    
    # Log final status
    logger.info("")
    logger.info("=" * 60)
    if all_tests_passed:
        logger.info("FINAL STATUS: TEST PASSED")
        logger.info("All security vulnerabilities have been identified and fixed.")
    else:
        logger.info("FINAL STATUS: TEST FAILED")
        logger.info("Some tests did not pass. Please review the logs above.")
    logger.info(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    return 0 if all_tests_passed else 1


if __name__ == "__main__":
    sys.exit(main())
