#!/usr/bin/env python3
"""
Fix Syntax Script

This script fixes syntax errors caused by style removal.
"""

import re
import os

def fix_file(file_path):
    """Fix syntax errors in a file"""
    print(f"Fixing syntax in {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix trailing commas in function calls
    content = re.sub(r',\s*,', ',', content)  # Remove double commas
    content = re.sub(r',\s*\)', ')', content)  # Remove trailing comma before closing paren
    content = re.sub(r',\s*\n\s*\)', '\n)', content)  # Remove trailing comma before closing paren on new line
    
    # Fix specific patterns
    content = re.sub(r'ttk\.Frame\([^)]*,\s*\)', lambda m: m.group(0).replace(', )', ')'), content)
    content = re.sub(r'ttk\.Label\([^)]*,\s*\)', lambda m: m.group(0).replace(', )', ')'), content)
    content = re.sub(r'ttk\.Button\([^)]*,\s*\)', lambda m: m.group(0).replace(', )', ')'), content)
    content = re.sub(r'ttk\.LabelFrame\([^)]*,\s*\)', lambda m: m.group(0).replace(', )', ')'), content)
    
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
    
    print("Syntax fixes completed!")

if __name__ == "__main__":
    main() 