#!/usr/bin/env python3
"""
System Python GUI Launcher

This script uses system Python to avoid virtual environment tkinter issues on macOS.
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Main entry point using system Python"""
    
    # Use system Python path
    system_python = "/opt/homebrew/bin/python3"
    
    if not os.path.exists(system_python):
        print("✗ System Python not found at /opt/homebrew/bin/python3")
        print("Please install Python via Homebrew: brew install python")
        return 1
    
    print("✓ Using system Python for GUI compatibility")
    
    # Test tkinter with system Python
    try:
        result = subprocess.run([
            system_python, '-c', 
            'import tkinter; root = tkinter.Tk(); root.destroy(); print("OK")'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            print(f"✗ System Python tkinter test failed: {result.stderr}")
            return 1
            
        print("✓ System Python tkinter test successful")
        
    except Exception as e:
        print(f"✗ System Python test failed: {e}")
        return 1
    
    # Launch the main application with system Python
    try:
        print("🚀 Launching TikTok Video Processing Tool with system Python...")
        
        # Set environment variables
        env = os.environ.copy()
        env['MACOSX_DEPLOYMENT_TARGET'] = '10.15'
        env['PYTHON_CONFIGURE_OPTS'] = '--enable-framework'
        
        # Run the main application
        result = subprocess.run([
            system_python, 'main.py'
        ], env=env)
        
        return result.returncode
        
    except Exception as e:
        print(f"✗ Application launch failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 