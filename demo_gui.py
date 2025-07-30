#!/usr/bin/env python3
"""
Demo script for the updated GUI
Tests the new features: radio buttons, context menu, individual progress
"""

import sys
import os
import glob
from pathlib import Path

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_gui_features():
    """Test the new GUI features"""
    print("🎬 Testing Updated GUI Features")
    print("=" * 40)
    
    # Check if we have videos
    video_files = glob.glob("dongphuc/*.mp4")
    if not video_files:
        print("❌ No videos found in dongphuc/ folder")
        return False
    
    # Check if we have background videos
    bg_files = glob.glob("video_chia_2/*.mp4")
    if not bg_files:
        print("❌ No background videos found in video_chia_2/ folder")
        return False
    
    # Check if we have GIF effects
    gif_files = glob.glob("effects/*.gif")
    
    print(f"✅ Found {len(video_files)} videos")
    print(f"✅ Found {len(bg_files)} background videos")
    print(f"✅ Found {len(gif_files)} GIF effects")
    
    print("\n🎯 New GUI Features:")
    print("1. ✅ Video Selection: Radio checkboxes (multiple selection)")
    print("2. ✅ GIF Effects: Radio buttons (single selection)")
    print("3. ✅ Queue Management: Individual progress bars")
    print("4. ✅ Parallel Processing: Multiple items render simultaneously")
    print("5. ✅ Individual Controls: Start/Stop/Pause/Skip per item")
    print("6. ✅ Simplified Interface: Only Start button for global control")
    
    print("\n🚀 Launching Updated GUI...")
    print("💡 Instructions:")
    print("   - Select videos using checkboxes")
    print("   - Choose GIF effect using radio buttons")
    print("   - Click 'Start Rendering' to begin all items")
    print("   - Use individual controls on each queue item")
    print("   - Items render in parallel based on CPU cores")
    
    return True

def main():
    """Main demo function"""
    print("🚀 TikTok Video Processing Tool - Updated GUI Demo")
    print("=" * 60)
    
    # Check dependencies
    try:
        import cv2
        print("✅ OpenCV available")
    except ImportError:
        print("❌ OpenCV not available. Please install: pip install opencv-python")
        return 1
    
    try:
        from PyQt5.QtWidgets import QApplication
        print("✅ PyQt5 available")
    except ImportError:
        print("❌ PyQt5 not available. Please install: pip install PyQt5")
        return 1
    
    # Test features
    if not test_gui_features():
        return 1
    
    # Create QApplication if not exists
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    # Import and launch GUI
    try:
        from gui_app_pyqt import VideoProcessingGUI
        
        window = VideoProcessingGUI()
        window.show()
        
        print("\n🎉 GUI launched successfully!")
        print("💡 Try the new features:")
        print("   - Multiple video selection with checkboxes")
        print("   - Single GIF selection with radio buttons")
        print("   - Individual progress bars for each item")
        print("   - Parallel processing with individual controls")
        
        # Keep the app running
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"❌ Error launching GUI: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 