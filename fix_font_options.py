#!/usr/bin/env python3
"""
Fix Font Options Script

This script removes all font options that are causing tkinter issues.
"""

import re
import os

def fix_file(file_path):
    """Fix font options in a file"""
    print(f"Fixing font options in {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove font options from ttk widgets
    content = re.sub(r'font=\([^)]*\)', '', content)
    content = re.sub(r'font="[^"]*"', '', content)
    content = re.sub(r'font=\'[^\']*\'', '', content)
    
    # Fix trailing commas and syntax errors
    content = re.sub(r',\s*,', ',', content)  # Remove double commas
    content = re.sub(r',\s*\)', ')', content)  # Remove trailing comma before closing paren
    content = re.sub(r',\s*\n\s*\)', '\n)', content)  # Remove trailing comma before closing paren on new line
    
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
    
    print("Font options fixes completed!")

if __name__ == "__main__":
    main() 