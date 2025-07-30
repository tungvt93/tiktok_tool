#!/usr/bin/env python3
"""
Launcher script for TikTok Video Processing Tool GUI (PyQt5 version)
Handles setup checks and error handling
"""

import sys
import os
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 7):
        print("❌ Error: Python 3.7 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True

def check_ffmpeg():
    """Check if FFmpeg is installed and accessible"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"✅ FFmpeg: {version_line}")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    print("❌ Error: FFmpeg not found or not accessible")
    print("Please install FFmpeg and ensure it's in your PATH")
    print("Download from: https://ffmpeg.org/download.html")
    return False

def check_dependencies():
    """Check if required Python packages are installed"""
    required_packages = ['PIL', 'numpy', 'PyQt5']
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'PIL':
                import PIL
            elif package == 'numpy':
                import numpy
            elif package == 'PyQt5':
                import PyQt5
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} - Missing")
    
    if missing_packages:
        print(f"\n❌ Missing packages: {', '.join(missing_packages)}")
        print("Please install required packages:")
        print("pip install -r requirements.txt")
        return False
    
    return True

def check_folders():
    """Check if required folders exist"""
    required_folders = ['dongphuc', 'video_chia_2', 'effects', 'output']
    missing_folders = []
    
    for folder in required_folders:
        if os.path.exists(folder):
            file_count = len(list(Path(folder).glob('*')))
            print(f"✅ {folder}/ ({file_count} files)")
        else:
            missing_folders.append(folder)
            print(f"❌ {folder}/ - Missing")
    
    if missing_folders:
        print(f"\n⚠️  Missing folders: {', '.join(missing_folders)}")
        print("Creating missing folders...")
        for folder in missing_folders:
            os.makedirs(folder, exist_ok=True)
            print(f"✅ Created {folder}/")
    
    return True

def main():
    """Main launcher function"""
    print("🚀 TikTok Video Processing Tool - PyQt5 GUI Launcher")
    print("=" * 55)
    
    # Check system requirements
    print("\n📋 System Requirements Check:")
    if not check_python_version():
        return 1
    
    if not check_ffmpeg():
        return 1
    
    if not check_dependencies():
        return 1
    
    # Check folder structure
    print("\n📁 Folder Structure Check:")
    check_folders()
    
    # Launch GUI
    print("\n🎬 Launching PyQt5 GUI Application...")
    try:
        from gui_app_pyqt import main as gui_main
        gui_main()
    except ImportError as e:
        print(f"❌ Error importing PyQt5 GUI: {e}")
        print("Make sure gui_app_pyqt.py exists in the current directory")
        return 1
    except Exception as e:
        print(f"❌ Error launching PyQt5 GUI: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 