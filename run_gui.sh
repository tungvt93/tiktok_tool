#!/bin/bash

echo "🚀 Starting TikTok Video Processing Tool GUI..."
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.7 or higher"
    exit 1
fi

# Check Python version
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
required_version="3.7"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Error: Python 3.7 or higher is required"
    echo "Current version: $python_version"
    exit 1
fi

echo "✅ Python version: $python_version"

# Run the launcher script
python3 run_gui.py

# Check exit code
if [ $? -ne 0 ]; then
    echo
    echo "❌ An error occurred. Please check the messages above."
    read -p "Press Enter to continue..."
fi 