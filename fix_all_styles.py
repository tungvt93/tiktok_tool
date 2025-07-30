#!/usr/bin/env python3
"""
Fix All Styles Script

This script removes all custom style references and fixes the UI completely.
"""

import re
import os

def fix_file(file_path):
    """Fix all style references in a file"""
    print(f"Fixing all styles in {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove all style references
    style_patterns = [
        r'style="[^"]*"',
        r'style=\'[^\']*\'',
    ]
    
    for pattern in style_patterns:
        content = re.sub(pattern, '', content)
    
    # Fix trailing commas and syntax errors
    content = re.sub(r',\s*,', ',', content)  # Remove double commas
    content = re.sub(r',\s*\)', ')', content)  # Remove trailing comma before closing paren
    content = re.sub(r',\s*\n\s*\)', '\n)', content)  # Remove trailing comma before closing paren on new line
    
    # Fix specific widget patterns
    content = re.sub(r'ttk\.Frame\([^)]*,\s*\)', lambda m: m.group(0).replace(', )', ')'), content)
    content = re.sub(r'ttk\.Label\([^)]*,\s*\)', lambda m: m.group(0).replace(', )', ')'), content)
    content = re.sub(r'ttk\.Button\([^)]*,\s*\)', lambda m: m.group(0).replace(', )', ')'), content)
    content = re.sub(r'ttk\.LabelFrame\([^)]*,\s*\)', lambda m: m.group(0).replace(', )', ')'), content)
    content = re.sub(r'ttk\.Entry\([^)]*,\s*\)', lambda m: m.group(0).replace(', )', ')'), content)
    content = re.sub(r'ttk\.Combobox\([^)]*,\s*\)', lambda m: m.group(0).replace(', )', ')'), content)
    content = re.sub(r'ttk\.Progressbar\([^)]*,\s*\)', lambda m: m.group(0).replace(', )', ')'), content)
    content = re.sub(r'ttk\.Spinbox\([^)]*,\s*\)', lambda m: m.group(0).replace(', )', ')'), content)
    
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
    
    print("All style fixes completed!")

if __name__ == "__main__":
    main() 