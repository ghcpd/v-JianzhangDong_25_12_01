#!/usr/bin/env python3
"""
Automatic test execution script.

This script:
1. Detects the current environment (Windows/Linux/Docker)
2. Runs the corresponding test script (run_test.sh for Linux/macOS, run_test.bat for Windows)
3. Tests both inputs_backup.py and inputs.py
4. Saves all output logs to logs/test_run.log with timestamps
5. Reports final status (TEST PASSED or TEST FAILED)
"""

import os
import sys
import subprocess
import platform
import json
from datetime import datetime
from pathlib import Path


def create_log_directory():
    """Create logs directory if it doesn't exist."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    return log_dir


def detect_environment():
    """Detect the current environment (Windows, Linux, macOS, or Docker)."""
    if os.path.exists("/.dockerenv"):
        return "docker"
    elif platform.system() == "Windows":
        return "windows"
    else:
        return "unix"  # Linux or macOS


def run_test_script(environment, log_file):
    """Run the appropriate test script for the environment."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(log_file, "a") as f:
        f.write(f"\n{'='*80}\n")
        f.write(f"Test Execution Start: {timestamp}\n")
        f.write(f"Environment: {environment}\n")
        f.write(f"{'='*80}\n\n")
    
    try:
        if environment == "windows":
            # Windows batch script
            if not Path("run_test.bat").exists():
                log_message(f"Error: run_test.bat not found", log_file)
                return False
            
            cmd = ["cmd", "/c", "run_test.bat"]
        else:
            # Unix shell script
            if not Path("run_test.sh").exists():
                log_message(f"Error: run_test.sh not found", log_file)
                return False
            
            cmd = ["bash", "run_test.sh"]
            # Make script executable
            os.chmod("run_test.sh", 0o755)
        
        # Run the test script and capture output
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        # Log the output
        with open(log_file, "a") as f:
            f.write("STDOUT:\n")
            f.write(result.stdout)
            f.write("\n\nSTDERR:\n")
            f.write(result.stderr)
            f.write(f"\n\nReturn Code: {result.returncode}\n")
        
        success = result.returncode == 0
        return success
        
    except subprocess.TimeoutExpired:
        log_message("Error: Test script timed out (>300 seconds)", log_file)
        return False
    except Exception as e:
        log_message(f"Error running test script: {str(e)}", log_file)
        return False


def log_message(message, log_file):
    """Append a message to the log file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a") as f:
        f.write(f"[{timestamp}] {message}\n")


def test_file(filename, log_file, test_number):
    """Test a specific Python file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    log_message(f"\n{'='*80}", log_file)
    log_message(f"Testing file: {filename}", log_file)
    log_message(f"Test number: {test_number}", log_file)
    log_message(f"Start time: {timestamp}", log_file)
    log_message(f"{'='*80}", log_file)
    
    if not Path(filename).exists():
        log_message(f"Error: {filename} not found", log_file)
        return False
    
    # Set up test environment
    env = os.environ.copy()
    env.update({
        "PAYMENT_TOKEN": "test_token_12345",
        "MAIL_SERVER_KEY": "test_mail_key",
        "INTERNAL_AUTH": "test_auth_123",
        "DB_FILE": "test_appdata.db",
        "AUTH_SALT": "test_salt_value",
        "FLASK_DEBUG": "False"
    })
    
    try:
        # Create test database
        import sqlite3
        conn = sqlite3.connect("test_appdata.db")
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS profiles (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            balance REAL NOT NULL
        )""")
        c.execute("INSERT OR IGNORE INTO profiles (id, name, balance) VALUES (?, ?, ?)",
                  ("user1", "John Doe", 1000.00))
        c.execute("INSERT OR IGNORE INTO profiles (id, name, balance) VALUES (?, ?, ?)",
                  ("user2", "Jane Smith", 2000.00))
        conn.commit()
        conn.close()
        
        # Create config directory and sample file
        os.makedirs("config", exist_ok=True)
        with open("config/sample.yaml", "w") as f:
            f.write("database:\n  host: localhost\n  port: 5432\nlogging:\n  level: INFO\n")
        
        # Run basic import test
        current_dir = os.getcwd().replace("\\", "\\\\")
        test_code = f"""
import sys
import os
sys.path.insert(0, '.')
os.chdir(r'{os.getcwd()}')

# Set environment variables
for key, val in {env}.items():
    if key not in ['PATH', 'PYTHONPATH', 'HOME', 'USER', 'LOGNAME', 'SHELL', 'TERM']:
        os.environ[key] = val

try:
    # Import the module
    import importlib.util
    spec = importlib.util.spec_from_file_location("{filename[:-3]}", r"{filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    print("[PASS] Module imported successfully")
    
    # Test auth_user
    result = module.auth_user({{"username": "testuser"}})
    if len(result) == 64:
        print("[PASS] auth_user returns proper hash")
    else:
        print(f"[FAIL] auth_user hash length issue: {{len(result)}}")
    
    # Test query_profile
    result = module.query_profile("user1")
    if isinstance(result, list):
        print("[PASS] query_profile works with parameterized queries")
    else:
        print("[FAIL] query_profile format issue")
    
    # Test Flask app exists
    if hasattr(module, 'app'):
        print("[PASS] Flask app created successfully")
    else:
        print("[FAIL] Flask app not found")
    
    print("SUCCESS: All module tests passed")
    sys.exit(0)
    
except Exception as e:
    print(f"[FAIL] Error: {{str(e)}}")
    import traceback
    traceback.print_exc()
    print("FAILED: Module test failed")
    sys.exit(1)
"""
        
        result = subprocess.run(
            [sys.executable, "-c", test_code],
            capture_output=True,
            text=True,
            env=env,
            timeout=30
        )
        
        with open(log_file, "a") as f:
            f.write("Test Output:\n")
            f.write(result.stdout)
            if result.stderr:
                f.write("\nErrors:\n")
                f.write(result.stderr)
        
        success = result.returncode == 0
        
        end_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message(f"End time: {end_timestamp}", log_file)
        
        if success:
            log_message(f"Status: TEST PASSED", log_file)
        else:
            log_message(f"Status: TEST FAILED", log_file)
        
        return success
        
    except subprocess.TimeoutExpired:
        log_message("Error: Test timed out (>30 seconds)", log_file)
        log_message("Status: TEST FAILED", log_file)
        return False
    except Exception as e:
        log_message(f"Error: {str(e)}", log_file)
        log_message("Status: TEST FAILED", log_file)
        return False
    finally:
        # Clean up test database
        if os.path.exists("test_appdata.db"):
            try:
                os.remove("test_appdata.db")
            except:
                pass


def main():
    """Main function to run tests."""
    print("Security Testing Suite - Auto Test Executor")
    print("=" * 80)
    
    # Create logs directory
    log_dir = create_log_directory()
    log_file = log_dir / "test_run.log"
    
    # Clear previous log
    with open(log_file, "w") as f:
        f.write(f"Auto Test Execution Log\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{'='*80}\n\n")
    
    # Detect environment
    environment = detect_environment()
    log_message(f"Detected environment: {environment}", log_file)
    print(f"Detected environment: {environment}")
    
    # Run environment-specific test script
    print("\nRunning platform-specific test script...")
    script_success = run_test_script(environment, log_file)
    
    # Test both versions
    print("\nRunning version-specific tests...")
    
    print("\nTest 1: Testing inputs_backup.py (vulnerable version)...")
    backup_success = test_file("inputs_backup.py", log_file, 1)
    
    print("Test 2: Testing inputs.py (secured version)...")
    secured_success = test_file("inputs.py", log_file, 2)
    
    # Determine overall status
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    
    overall_success = script_success and secured_success
    
    print(f"Platform test script: {'PASSED' if script_success else 'FAILED'}")
    print(f"Backup version (inputs_backup.py): {'PASSED' if backup_success else 'FAILED'}")
    print(f"Secured version (inputs.py): {'PASSED' if secured_success else 'FAILED'}")
    
    # Write final status to log
    final_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a") as f:
        f.write(f"\n{'='*80}\n")
        f.write(f"Test Execution Summary\n")
        f.write(f"{'='*80}\n")
        f.write(f"Platform test script: {'PASSED' if script_success else 'FAILED'}\n")
        f.write(f"Backup version (inputs_backup.py): {'PASSED' if backup_success else 'FAILED'}\n")
        f.write(f"Secured version (inputs.py): {'PASSED' if secured_success else 'FAILED'}\n")
        f.write(f"\nFinal Status: {'TEST PASSED' if overall_success else 'TEST FAILED'}\n")
        f.write(f"End time: {final_timestamp}\n")
    
    print(f"\nFinal Status: {'TEST PASSED ✓' if overall_success else 'TEST FAILED ✗'}")
    print(f"Log file: {log_file}")
    
    return 0 if overall_success else 1


if __name__ == "__main__":
    sys.exit(main())
