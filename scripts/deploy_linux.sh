#!/bin/bash
# Linux Deployment Script for TikTok Video Processing Tool

set -e  # Exit on any error

echo "TikTok Video Processing Tool - Linux Deployment"
echo "============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Detect Linux distribution
detect_distro() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        DISTRO=$ID
        VERSION=$VERSION_ID
    elif [[ -f /etc/redhat-release ]]; then
        DISTRO="rhel"
    elif [[ -f /etc/debian_version ]]; then
        DISTRO="debian"
    else
        DISTRO="unknown"
    fi
    
    print_status "Detected distribution: $DISTRO $VERSION"
}

# Install system dependencies
install_system_deps() {
    print_status "Installing system dependencies..."
    
    case $DISTRO in
        ubuntu|debian)
            sudo apt-get update
            sudo apt-get install -y python3 python3-pip python3-venv ffmpeg
            ;;
        fedora)
            sudo dnf install -y python3 python3-pip ffmpeg
            ;;
        centos|rhel)
            # Enable EPEL repository for FFmpeg
            sudo yum install -y epel-release
            sudo yum install -y python3 python3-pip ffmpeg
            ;;
        arch)
            sudo pacman -S --noconfirm python python-pip ffmpeg
            ;;
        opensuse*)
            sudo zypper install -y python3 python3-pip ffmpeg
            ;;
        *)
            print_warning "Unknown distribution. Please install manually:"
            echo "  - Python 3.8 or higher"
            echo "  - pip (Python package manager)"
            echo "  - FFmpeg"
            read -p "Continue assuming dependencies are installed? (y/n): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
            ;;
    esac
}

# Check if Python 3 is installed
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        return 1
    fi
    
    # Check Python version
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    print_status "Found Python $PYTHON_VERSION"
    
    # Check if version is 3.8 or higher
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
    
    if [[ $PYTHON_MAJOR -lt 3 ]] || [[ $PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -lt 8 ]]; then
        print_error "Python 3.8 or higher is required (found $PYTHON_VERSION)"
        return 1
    fi
    
    return 0
}

# Check if FFmpeg is installed
check_ffmpeg() {
    if ! command -v ffmpeg &> /dev/null; then
        print_warning "FFmpeg is not installed"
        return 1
    else
        print_status "FFmpeg is available"
        return 0
    fi
}

# Main installation function
install_application() {
    # Detect distribution
    detect_distro
    
    # Check dependencies
    if ! check_python || ! check_ffmpeg; then
        print_info "Installing missing dependencies..."
        install_system_deps
        
        # Re-check after installation
        if ! check_python; then
            print_error "Python installation failed"
            exit 1
        fi
        
        if ! check_ffmpeg; then
            print_warning "FFmpeg installation may have failed"
            print_info "The application requires FFmpeg to function properly"
        fi
    fi
    
    # Set installation directory
    INSTALL_DIR="$HOME/.local/share/tiktok-video-processor"
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
    
    # Command-line wrapper
    cat > "$INSTALL_DIR/tiktok-processor" << EOF
#!/bin/bash
cd "$INSTALL_DIR"
source venv/bin/activate
python main.py "\$@"
EOF
    
    chmod +x "$INSTALL_DIR/tiktok-processor"
    
    # GUI launcher script
    cat > "$INSTALL_DIR/tiktok-processor-gui" << EOF
#!/bin/bash
cd "$INSTALL_DIR"
source venv/bin/activate
python main.py
EOF
    
    chmod +x "$INSTALL_DIR/tiktok-processor-gui"
    
    # Create symlinks for command-line access
    BIN_DIR="$HOME/.local/bin"
    mkdir -p "$BIN_DIR"
    
    ln -sf "$INSTALL_DIR/tiktok-processor" "$BIN_DIR/tiktok-processor"
    ln -sf "$INSTALL_DIR/tiktok-processor-gui" "$BIN_DIR/tiktok-processor-gui"
    
    print_status "Command-line tools installed in $BIN_DIR"
    
    # Add to PATH if not already there
    if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
        print_info "Adding $BIN_DIR to PATH..."
        
        # Add to .bashrc
        if [[ -f "$HOME/.bashrc" ]]; then
            echo "export PATH=\"\$PATH:$BIN_DIR\"" >> "$HOME/.bashrc"
        fi
        
        # Add to .profile
        if [[ -f "$HOME/.profile" ]]; then
            echo "export PATH=\"\$PATH:$BIN_DIR\"" >> "$HOME/.profile"
        fi
        
        print_info "Please restart your terminal or run: source ~/.bashrc"
    fi
    
    # Create desktop entry (if desktop environment is available)
    if [[ -n "$XDG_CURRENT_DESKTOP" ]]; then
        print_status "Creating desktop entry..."
        
        DESKTOP_DIR="$HOME/.local/share/applications"
        mkdir -p "$DESKTOP_DIR"
        
        cat > "$DESKTOP_DIR/tiktok-video-processor.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=TikTok Video Processor
Comment=Process videos with effects for TikTok
Exec=$INSTALL_DIR/tiktok-processor-gui
Icon=video-x-generic
Terminal=false
Categories=AudioVideo;Video;
Keywords=video;processing;tiktok;effects;
EOF
        
        chmod +x "$DESKTOP_DIR/tiktok-video-processor.desktop"
        
        # Update desktop database
        if command -v update-desktop-database &> /dev/null; then
            update-desktop-database "$DESKTOP_DIR"
        fi
        
        print_status "Desktop entry created"
    fi
    
    # Create systemd user service (optional)
    read -p "Create systemd service for batch processing? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Creating systemd service..."
        
        SYSTEMD_DIR="$HOME/.config/systemd/user"
        mkdir -p "$SYSTEMD_DIR"
        
        cat > "$SYSTEMD_DIR/tiktok-processor.service" << EOF
[Unit]
Description=TikTok Video Processor Batch Service
After=network.target

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python main.py --cli list
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF
        
        # Reload systemd and enable service
        systemctl --user daemon-reload
        systemctl --user enable tiktok-processor.service
        
        print_status "Systemd service created and enabled"
        print_info "Control with: systemctl --user start/stop/status tiktok-processor"
    fi
    
    # Create uninstaller
    print_status "Creating uninstaller..."
    cat > "$INSTALL_DIR/uninstall.sh" << EOF
#!/bin/bash
echo "Uninstalling TikTok Video Processing Tool..."

# Remove installation directory
rm -rf "$INSTALL_DIR"

# Remove symlinks
rm -f "$HOME/.local/bin/tiktok-processor"
rm -f "$HOME/.local/bin/tiktok-processor-gui"

# Remove desktop entry
rm -f "$HOME/.local/share/applications/tiktok-video-processor.desktop"

# Remove systemd service
systemctl --user stop tiktok-processor.service 2>/dev/null || true
systemctl --user disable tiktok-processor.service 2>/dev/null || true
rm -f "$HOME/.config/systemd/user/tiktok-processor.service"
systemctl --user daemon-reload 2>/dev/null || true

# Update desktop database
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi

echo "Uninstallation complete."
echo "Note: PATH modifications in ~/.bashrc and ~/.profile were not removed."
EOF
    
    chmod +x "$INSTALL_DIR/uninstall.sh"
    
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
    echo "============================================="
    print_status "Installation completed successfully!"
    echo "============================================="
    echo
    echo "Installation directory: $INSTALL_DIR"
    echo
    echo "To run the application:"
    echo "  Command line: tiktok-processor --help"
    echo "  GUI mode:     tiktok-processor-gui"
    echo "  CLI mode:     tiktok-processor --cli list"
    echo
    if [[ -n "$XDG_CURRENT_DESKTOP" ]]; then
        echo "  Desktop:      Available in applications menu"
    fi
    echo
    echo "Configuration:"
    echo "  Show config:  tiktok-processor --config-info"
    echo "  Create config: tiktok-processor --create-config"
    echo
    echo "To uninstall: Run $INSTALL_DIR/uninstall.sh"
    echo
    
    # Check if PATH needs to be updated
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        print_warning "Please restart your terminal or run: source ~/.bashrc"
    fi
}

# Main execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    install_application
fi