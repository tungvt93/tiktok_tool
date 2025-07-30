#!/usr/bin/env python3
"""
GUI Launcher Script

This script handles macOS tkinter compatibility issues and launches the GUI application.
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Main entry point"""
    # Set environment variables to handle macOS compatibility
    os.environ['MACOSX_DEPLOYMENT_TARGET'] = '10.15'
    os.environ['PYTHON_CONFIGURE_OPTS'] = '--enable-framework'
    
    # Try to import tkinter with error handling
    try:
        import tkinter as tk
        print("✓ Tkinter is available")
    except ImportError as e:
        print(f"✗ Tkinter import failed: {e}")
        print("Please install tkinter:")
        print("  - On macOS: brew install python-tk")
        print("  - On Ubuntu: sudo apt-get install python3-tk")
        print("  - On CentOS: sudo yum install tkinter")
        return 1
    except Exception as e:
        print(f"✗ Tkinter error: {e}")
        return 1
    
    # Try to create a test window
    try:
        root = tk.Tk()
        root.withdraw()  # Hide the window
        root.destroy()
        print("✓ Tkinter window creation successful")
    except Exception as e:
        print(f"✗ Tkinter window creation failed: {e}")
        print("This might be a macOS compatibility issue.")
        print("Trying alternative approach...")
        
        # Try with different Python executable
        try:
            result = subprocess.run([
                sys.executable, '-c', 
                'import tkinter; root = tkinter.Tk(); root.destroy(); print("OK")'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print("✓ Alternative tkinter test successful")
            else:
                print(f"✗ Alternative tkinter test failed: {result.stderr}")
                return 1
        except Exception as e:
            print(f"✗ Alternative approach failed: {e}")
            return 1
    
    # Launch the main application
    try:
        print("🚀 Launching TikTok Video Processing Tool...")
        
        # Import and run the main application
        from main import main as main_app
        return main_app()
        
    except Exception as e:
        print(f"✗ Application launch failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 