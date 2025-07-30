#!/bin/bash
# Docker entrypoint script for TikTok Video Processing Tool

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[DOCKER]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[DOCKER]${NC} $1"
}

print_error() {
    echo -e "${RED}[DOCKER]${NC} $1"
}

# Function to wait for dependencies
wait_for_dependencies() {
    print_status "Checking dependencies..."
    
    # Check if FFmpeg is available
    if ! command -v ffmpeg &> /dev/null; then
        print_error "FFmpeg is not available in the container"
        exit 1
    fi
    
    # Check if Python modules are available
    if ! python -c "import src" 2>/dev/null; then
        print_error "Application modules are not available"
        exit 1
    fi
    
    print_status "Dependencies check passed"
}

# Function to setup directories
setup_directories() {
    print_status "Setting up directories..."
    
    # Ensure required directories exist
    mkdir -p /app/input /app/output /app/config /app/logs
    
    # Set proper permissions
    chown -R appuser:appuser /app/input /app/output /app/config /app/logs 2>/dev/null || true
    
    print_status "Directories setup completed"
}

# Function to initialize configuration
init_config() {
    if [[ ! -f /app/config.json ]]; then
        print_status "Creating default configuration..."
        python main.py --create-config
    else
        print_status "Using existing configuration"
    fi
    
    # Validate configuration
    if ! python main.py --validate-config > /dev/null 2>&1; then
        print_warning "Configuration validation failed - using defaults"
    fi
}

# Function to handle different run modes
handle_run_mode() {
    local mode="${1:-help}"
    
    case "$mode" in
        "gui")
            print_error "GUI mode is not supported in Docker containers"
            print_status "Use CLI mode instead: docker run ... cli"
            exit 1
            ;;
        "cli")
            shift
            print_status "Running in CLI mode with args: $*"
            exec python main.py --cli "$@"
            ;;
        "batch")
            print_status "Running in batch processing mode"
            exec python main.py --cli process /app/input/*.mp4 /app/input/background.mp4
            ;;
        "config")
            print_status "Running configuration management"
            exec python main.py --cli config show
            ;;
        "validate")
            print_status "Validating installation"
            python main.py --validate-config
            python main.py --cli effects
            print_status "Validation completed successfully"
            ;;
        "shell"|"bash")
            print_status "Starting interactive shell"
            exec /bin/bash
            ;;
        "help"|*)
            print_status "Available run modes:"
            echo "  cli [args]    - Run in CLI mode with arguments"
            echo "  batch         - Run batch processing on input directory"
            echo "  config        - Show configuration"
            echo "  validate      - Validate installation"
            echo "  shell         - Start interactive shell"
            echo "  help          - Show this help"
            echo
            echo "Examples:"
            echo "  docker run ... cli list"
            echo "  docker run ... cli process input.mp4 bg.mp4 -o output.mp4"
            echo "  docker run ... batch"
            echo "  docker run ... validate"
            
            if [[ "$mode" == "help" ]]; then
                exit 0
            else
                exec python main.py --help
            fi
            ;;
    esac
}

# Main entrypoint logic
main() {
    print_status "TikTok Video Processing Tool - Docker Container"
    print_status "Version: 2.0.0"
    
    # Wait for dependencies
    wait_for_dependencies
    
    # Setup directories
    setup_directories
    
    # Initialize configuration
    init_config
    
    # Handle different run modes
    if [[ $# -eq 0 ]]; then
        handle_run_mode "help"
    else
        handle_run_mode "$@"
    fi
}

# Execute main function with all arguments
main "$@"