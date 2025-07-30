#!/bin/bash
# macOS Deployment Script for TikTok Video Processing Tool

set -e  # Exit on any error

echo "TikTok Video Processing Tool - macOS Deployment"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    print_error "This script is designed for macOS only"
    exit 1
fi

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    echo "Please install Python 3.8 or higher:"
    echo "  - Download from https://python.org"
    echo "  - Or install via Homebrew: brew install python"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
print_status "Found Python $PYTHON_VERSION"

# Check if version is 3.8 or higher
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

if [[ $PYTHON_MAJOR -lt 3 ]] || [[ $PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -lt 8 ]]; then
    print_error "Python 3.8 or higher is required (found $PYTHON_VERSION)"
    exit 1
fi

# Check if FFmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    print_warning "FFmpeg is not installed"
    echo "The application requires FFmpeg to function properly."
    echo "Install options:"
    echo "  - Homebrew: brew install ffmpeg"
    echo "  - MacPorts: sudo port install ffmpeg"
    echo "  - Download from: https://ffmpeg.org/download.html"
    
    read -p "Continue without FFmpeg? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    print_status "FFmpeg is available"
fi

# Set installation directory
INSTALL_DIR="$HOME/Applications/TikTokVideoProcessor"
print_status "Installation directory: $INSTALL_DIR"

# Create installation directory
mkdir -p "$INSTALL_DIR"

# Copy application files
print_status "Copying application files..."
cp -r src "$INSTALL_DIR/"
cp main.py "$INSTALL_DIR/"
cp requirements.txt "$INSTALL_DIR/"
cp README.md "$INSTALL_DIR/"
cp CHANGELOG.md "$INSTALL_DIR/" 2>/dev/null || true

# Copy configuration files
if [[ -f "config.json" ]]; then
    cp config.json "$INSTALL_DIR/"
fi

if [[ -f "config/default.json" ]]; then
    mkdir -p "$INSTALL_DIR/config"
    cp config/default.json "$INSTALL_DIR/config/"
fi

# Create virtual environment
print_status "Creating virtual environment..."
cd "$INSTALL_DIR"
python3 -m venv venv

# Activate virtual environment and install dependencies
print_status "Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

if [[ $? -ne 0 ]]; then
    print_error "Failed to install Python dependencies"
    exit 1
fi

# Create launcher scripts
print_status "Creating launcher scripts..."

# GUI launcher
cat > "$INSTALL_DIR/TikTokProcessor-GUI.command" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python main.py
EOF

# CLI launcher
cat > "$INSTALL_DIR/TikTokProcessor-CLI.command" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python main.py --cli "$@"
EOF

# Configuration launcher
cat > "$INSTALL_DIR/TikTokProcessor-Config.command" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python main.py --config-info
read -p "Press Enter to continue..."
EOF

# Make scripts executable
chmod +x "$INSTALL_DIR"/*.command

# Create command-line wrapper
print_status "Creating command-line wrapper..."
cat > "$INSTALL_DIR/tiktok-processor" << EOF
#!/bin/bash
cd "$INSTALL_DIR"
source venv/bin/activate
python main.py "\$@"
EOF

chmod +x "$INSTALL_DIR/tiktok-processor"

# Create symlink for command-line access
SYMLINK_DIR="/usr/local/bin"
if [[ -w "$SYMLINK_DIR" ]]; then
    ln -sf "$INSTALL_DIR/tiktok-processor" "$SYMLINK_DIR/tiktok-processor"
    print_status "Command-line tool installed: tiktok-processor"
else
    print_warning "Cannot create symlink in $SYMLINK_DIR (permission denied)"
    echo "To use from command line, add to your PATH or run:"
    echo "  sudo ln -sf '$INSTALL_DIR/tiktok-processor' '$SYMLINK_DIR/tiktok-processor'"
fi

# Create .app bundle (optional)
read -p "Create macOS .app bundle? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "Creating .app bundle..."
    
    APP_DIR="$HOME/Applications/TikTok Video Processor.app"
    mkdir -p "$APP_DIR/Contents/MacOS"
    mkdir -p "$APP_DIR/Contents/Resources"
    
    # Create Info.plist
    cat > "$APP_DIR/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>TikTokProcessor</string>
    <key>CFBundleIdentifier</key>
    <string>com.tiktokprocessor.app</string>
    <key>CFBundleName</key>
    <string>TikTok Video Processor</string>
    <key>CFBundleVersion</key>
    <string>2.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>2.0.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.14</string>
</dict>
</plist>
EOF
    
    # Create app executable
    cat > "$APP_DIR/Contents/MacOS/TikTokProcessor" << EOF
#!/bin/bash
cd "$INSTALL_DIR"
source venv/bin/activate
python main.py
EOF
    
    chmod +x "$APP_DIR/Contents/MacOS/TikTokProcessor"
    
    print_status ".app bundle created: $APP_DIR"
fi

# Create uninstaller
print_status "Creating uninstaller..."
cat > "$INSTALL_DIR/Uninstall.command" << EOF
#!/bin/bash
echo "Uninstalling TikTok Video Processing Tool..."
rm -rf "$INSTALL_DIR"
rm -f "/usr/local/bin/tiktok-processor"
rm -rf "$HOME/Applications/TikTok Video Processor.app"
echo "Uninstallation complete."
read -p "Press Enter to continue..."
EOF

chmod +x "$INSTALL_DIR/Uninstall.command"

# Test installation
print_status "Testing installation..."
cd "$INSTALL_DIR"
source venv/bin/activate
python main.py --help > /dev/null 2>&1

if [[ $? -ne 0 ]]; then
    print_error "Installation test failed"
    exit 1
fi

# Success message
echo
echo "=============================================="
print_status "Installation completed successfully!"
echo "=============================================="
echo
echo "Installation directory: $INSTALL_DIR"
echo
echo "To run the application:"
echo "  GUI Mode: Double-click TikTokProcessor-GUI.command"
echo "  CLI Mode: Run TikTokProcessor-CLI.command or use 'tiktok-processor' command"
echo "  Config:   Double-click TikTokProcessor-Config.command"
echo
if [[ -d "$HOME/Applications/TikTok Video Processor.app" ]]; then
    echo "  App Bundle: Available in Applications folder"
fi
echo
echo "To uninstall: Run Uninstall.command in the installation directory"
echo

# Open installation directory
read -p "Open installation directory in Finder? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    open "$INSTALL_DIR"
fi