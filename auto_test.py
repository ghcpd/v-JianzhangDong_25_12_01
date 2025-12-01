#!/usr/bin/env python3
"""
Automatic Test Execution Script
This script detects the current environment and runs appropriate test scripts
"""

import os
import sys
import platform
import subprocess
from datetime import datetime
import pathlib


class AutoTester:
    """Automatic test runner with environment detection"""
    
    def __init__(self):
        self.system = platform.system()
        self.log_dir = "logs"
        self.log_file = os.path.join(self.log_dir, "test_run.log")
        self.ensure_log_directory()
        
    def ensure_log_directory(self):
        """Create logs directory if it doesn't exist"""
        os.makedirs(self.log_dir, exist_ok=True)
        
    def get_timestamp(self):
        """Get formatted timestamp"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def log_message(self, message, print_to_console=True):
        """Log message to file and optionally to console"""
        timestamp = self.get_timestamp()
        log_entry = f"[{timestamp}] {message}\n"
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
        
        if print_to_console:
            print(f"[{timestamp}] {message}")
    
    def detect_environment(self):
        """Detect the current operating environment"""
        self.log_message("=" * 60)
        self.log_message("Automatic Test Runner - Environment Detection")
        self.log_message("=" * 60)
        
        # Check if running in Docker
        if os.path.exists("/.dockerenv") or os.path.exists("/run/.containerenv"):
            self.log_message("Environment: Docker Container")
            return "docker"
        
        # Check operating system
        if self.system == "Windows":
            self.log_message(f"Environment: Windows ({platform.release()})")
            return "windows"
        elif self.system in ["Linux", "Darwin"]:
            self.log_message(f"Environment: {self.system} ({platform.release()})")
            return "linux"
        else:
            self.log_message(f"Environment: Unknown ({self.system})")
            return "unknown"
    
    def run_windows_test(self):
        """Run Windows batch test script"""
        self.log_message("Running Windows test script (run_test.bat)...")
        
        try:
            # Run the batch file
            result = subprocess.run(
                ["cmd.exe", "/c", "run_test.bat"],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Log output
            self.log_message("=" * 60)
            self.log_message("Test Output:")
            self.log_message("-" * 60)
            
            output = result.stdout
            if result.stderr:
                output += "\n" + result.stderr
            
            for line in output.split("\n"):
                if line.strip():
                    self.log_message(line, print_to_console=False)
            
            self.log_message("-" * 60)
            
            # Determine status
            if result.returncode == 0:
                self.log_message("Status: TEST PASSED")
                return True
            else:
                self.log_message("Status: TEST FAILED")
                return False
                
        except subprocess.TimeoutExpired:
            self.log_message("ERROR: Test execution timed out")
            self.log_message("Status: TEST FAILED")
            return False
        except FileNotFoundError:
            self.log_message("ERROR: run_test.bat not found")
            self.log_message("Status: TEST FAILED")
            return False
        except Exception as e:
            self.log_message(f"ERROR: {str(e)}")
            self.log_message("Status: TEST FAILED")
            return False
    
    def run_linux_test(self):
        """Run Linux/macOS shell test script"""
        self.log_message("Running Linux/macOS test script (run_test.sh)...")
        
        # Make script executable
        try:
            os.chmod("run_test.sh", 0o755)
        except Exception as e:
            self.log_message(f"Warning: Could not set execute permission: {e}")
        
        try:
            # Determine shell
            shell = "/bin/bash"
            if not os.path.exists(shell):
                shell = "/bin/sh"
            
            # Run the shell script
            result = subprocess.run(
                [shell, "run_test.sh"],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Log output
            self.log_message("=" * 60)
            self.log_message("Test Output:")
            self.log_message("-" * 60)
            
            output = result.stdout
            if result.stderr:
                output += "\n" + result.stderr
            
            for line in output.split("\n"):
                if line.strip():
                    self.log_message(line, print_to_console=False)
            
            self.log_message("-" * 60)
            
            # Determine status
            if result.returncode == 0:
                self.log_message("Status: TEST PASSED")
                return True
            else:
                self.log_message("Status: TEST FAILED")
                return False
                
        except subprocess.TimeoutExpired:
            self.log_message("ERROR: Test execution timed out")
            self.log_message("Status: TEST FAILED")
            return False
        except FileNotFoundError:
            self.log_message("ERROR: run_test.sh not found")
            self.log_message("Status: TEST FAILED")
            return False
        except Exception as e:
            self.log_message(f"ERROR: {str(e)}")
            self.log_message("Status: TEST FAILED")
            return False
    
    def run_docker_test(self):
        """Run tests in Docker environment"""
        self.log_message("Running tests in Docker environment...")
        # In Docker, we're likely on Linux
        return self.run_linux_test()
    
    def run_tests(self):
        """Main test execution function"""
        # Detect environment
        env = self.detect_environment()
        self.log_message("")
        
        # Run appropriate test
        if env == "windows":
            success = self.run_windows_test()
        elif env == "linux":
            success = self.run_linux_test()
        elif env == "docker":
            success = self.run_docker_test()
        else:
            self.log_message("ERROR: Unsupported environment")
            self.log_message("Status: TEST FAILED")
            success = False
        
        # Final summary
        self.log_message("")
        self.log_message("=" * 60)
        self.log_message("Test Execution Complete")
        self.log_message("=" * 60)
        self.log_message(f"Log file: {self.log_file}")
        
        if success:
            self.log_message("FINAL STATUS: TEST PASSED")
            return 0
        else:
            self.log_message("FINAL STATUS: TEST FAILED")
            return 1


def main():
    """Main entry point"""
    try:
        tester = AutoTester()
        exit_code = tester.run_tests()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTest execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\nFATAL ERROR: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
