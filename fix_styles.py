#!/usr/bin/env python3
"""
Fix Styles Script

This script temporarily removes custom style references to fix tkinter compatibility.
"""

import re
import os
from pathlib import Path

def fix_file(file_path):
    """Fix style references in a file"""
    print(f"Fixing {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove style="Card.TFrame" and style="Card.TLabelFrame"
    content = re.sub(r'style="Card\.TFrame"', '', content)
    content = re.sub(r'style="Card\.TLabelFrame"', '', content)
    content = re.sub(r'style="Main\.TFrame"', '', content)
    content = re.sub(r'style="Primary\.TButton"', '', content)
    content = re.sub(r'style="Secondary\.TButton"', '', content)
    content = re.sub(r'style="Custom\.TEntry"', '', content)
    content = re.sub(r'style="Custom\.TCombobox"', '', content)
    content = re.sub(r'style="Custom\.Horizontal\.TProgressbar"', '', content)
    content = re.sub(r'style="Main\.TLabel"', '', content)
    content = re.sub(r'style="Main\.TCheckbutton"', '', content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    """Main function"""
    files_to_fix = [
        'src/presentation/gui/main_window.py',
        'src/presentation/gui/components/video_list_widget.py',
        'src/presentation/gui/components/progress_widget.py',
        'src/presentation/gui/components/effects_config_widget.py'
    ]
    
    for file_path in files_to_fix:
        if os.path.exists(file_path):
            fix_file(file_path)
        else:
            print(f"File not found: {file_path}")
    
    print("Style fixes completed!")

if __name__ == "__main__":
    main() 