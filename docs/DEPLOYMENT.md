# Deployment Guide

This guide covers deployment options for the TikTok Video Processing Tool across different platforms and environments.

## Quick Start

### Automated Deployment Scripts

Platform-specific deployment scripts are available in the `scripts/` directory:

- **Windows**: `scripts/deploy_windows.bat`
- **macOS**: `scripts/deploy_macos.sh`
- **Linux**: `scripts/deploy_linux.sh`

Simply run the appropriate script for your platform:

```bash
# macOS/Linux
chmod +x scripts/deploy_macos.sh
./scripts/deploy_macos.sh

# Windows (run as Administrator)
scripts\deploy_windows.bat
```

## Manual Installation

### Prerequisites

All platforms require:

- Python 3.8 or higher
- FFmpeg (for video processing)
- pip (Python package manager)

### Installation Steps

1. **Clone or download the application**
2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Create configuration**:
   ```bash
   python main.py --create-config
   ```
4. **Test installation**:
   ```bash
   python main.py --help
   ```

## Platform-Specific Deployment

### Windows Deployment

#### System Requirements

- Windows 10 or later
- Python 3.8+ from python.org
- FFmpeg from https://ffmpeg.org/download.html

#### Automated Installation

```cmd
scripts\deploy_windows.bat
```

#### Manual Installation

1. Install Python from https://python.org
2. Install FFmpeg and add to PATH
3. Run installation commands:
   ```cmd
   pip install -r requirements.txt
   python main.py --create-config
   ```

#### Features

- Desktop shortcuts
- Start menu integration
- Batch file launchers
- Automatic uninstaller

### macOS Deployment

#### System Requirements

- macOS 10.14 (Mojave) or later
- Python 3.8+ (via Homebrew or python.org)
- FFmpeg (via Homebrew: `brew install ffmpeg`)

#### Automated Installation

```bash
chmod +x scripts/deploy_macos.sh
./scripts/deploy_macos.sh
```

#### Manual Installation

1. Install Homebrew: https://brew.sh
2. Install dependencies:
   ```bash
   brew install python ffmpeg
   ```
3. Run installation commands:
   ```bash
   pip3 install -r requirements.txt
   python3 main.py --create-config
   ```

#### Features

- .app bundle creation
- Command-line tools
- Finder integration
- Automatic PATH setup

### Linux Deployment

#### System Requirements

- Modern Linux distribution (Ubuntu 18.04+, Fedora 30+, etc.)
- Python 3.8+
- FFmpeg

#### Automated Installation

```bash
chmod +x scripts/deploy_linux.sh
./scripts/deploy_linux.sh
```

#### Manual Installation

**Ubuntu/Debian:**

```bash
sudo apt-get update
sudo apt-get install python3 python3-pip python3-venv ffmpeg
pip3 install -r requirements.txt
```

**Fedora:**

```bash
sudo dnf install python3 python3-pip ffmpeg
pip3 install -r requirements.txt
```

**Arch Linux:**

```bash
sudo pacman -S python python-pip ffmpeg
pip install -r requirements.txt
```

#### Features

- Desktop entry creation
- Systemd service support
- Command-line integration
- XDG compliance

## Docker Deployment

### Quick Start with Docker

1. **Build the image**:

   ```bash
   docker build -f docker/Dockerfile -t tiktok-video-processor .
   ```

2. **Run with Docker Compose**:
   ```bash
   cd docker
   docker-compose up
   ```

### Docker Commands

```bash
# List videos
docker run --rm -v $(pwd)/input:/app/input tiktok-video-processor cli list

# Process single video
docker run --rm \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  tiktok-video-processor cli process input.mp4 background.mp4 -o output.mp4

# Batch processing
docker-compose --profile batch up

# Configuration management
docker-compose --profile config up
```

### Docker Environment Variables

- `LOG_LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR)
- `PYTHONUNBUFFERED`: Enable unbuffered Python output
- `MAX_WORKERS`: Override maximum worker threads

### Docker Volumes

- `/app/input`: Input video files
- `/app/output`: Processed output files
- `/app/config`: Configuration files
- `/app/logs`: Application logs

## Cloud Deployment

### AWS EC2

1. **Launch EC2 instance** (Ubuntu 20.04 LTS recommended)
2. **Install dependencies**:
   ```bash
   sudo apt-get update
   sudo apt-get install python3 python3-pip ffmpeg
   ```
3. **Deploy application**:
   ```bash
   git clone <repository>
   cd tiktok-video-processor
   ./scripts/deploy_linux.sh
   ```

### Google Cloud Platform

1. **Create Compute Engine instance**
2. **Use startup script**:
   ```bash
   #!/bin/bash
   apt-get update
   apt-get install -y python3 python3-pip ffmpeg git
   git clone <repository> /opt/tiktok-processor
   cd /opt/tiktok-processor
   ./scripts/deploy_linux.sh
   ```

### Azure Virtual Machine

1. **Create Ubuntu VM**
2. **Use cloud-init**:
   ```yaml
   #cloud-config
   packages:
     - python3
     - python3-pip
     - ffmpeg
     - git
   runcmd:
     - git clone <repository> /opt/tiktok-processor
     - cd /opt/tiktok-processor && ./scripts/deploy_linux.sh
   ```

## Production Deployment

### System Service Setup

#### systemd (Linux)

Create service file `/etc/systemd/system/tiktok-processor.service`:

```ini
[Unit]
Description=TikTok Video Processing Service
After=network.target

[Service]
Type=simple
User=tiktok-processor
WorkingDirectory=/opt/tiktok-processor
ExecStart=/opt/tiktok-processor/venv/bin/python main.py --cli list
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable tiktok-processor
sudo systemctl start tiktok-processor
```

#### launchd (macOS)

Create plist file `~/Library/LaunchAgents/com.tiktokprocessor.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.tiktokprocessor</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/path/to/main.py</string>
        <string>--cli</string>
        <string>list</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

Load service:

```bash
launchctl load ~/Library/LaunchAgents/com.tiktokprocessor.plist
```

### Reverse Proxy Setup (Nginx)

For web interface deployment:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /opt/tiktok-processor/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

## Monitoring and Logging

### Log Configuration

Configure logging in `config.json`:

```json
{
  "ui": {
    "log_level": "INFO"
  }
}
```

### Log Locations

- **Linux**: `~/.local/share/tiktok-video-processor/logs/`
- **macOS**: `~/Applications/TikTokVideoProcessor/logs/`
- **Windows**: `%USERPROFILE%\TikTokVideoProcessor\logs\`
- **Docker**: `/app/logs/`

### Monitoring Tools

#### Prometheus Metrics (Future Enhancement)

```python
# Example metrics endpoint
from prometheus_client import Counter, Histogram, generate_latest

VIDEOS_PROCESSED = Counter('videos_processed_total', 'Total processed videos')
PROCESSING_TIME = Histogram('video_processing_seconds', 'Video processing time')
```

#### Health Checks

```bash
# Basic health check
curl -f http://localhost:8000/health || exit 1

# CLI health check
python main.py --validate-config
```

## Security Considerations

### File Permissions

Ensure proper file permissions:

```bash
# Application files
chmod 755 main.py
chmod -R 644 src/
chmod -R 755 scripts/

# Configuration files
chmod 600 config.json
chmod 700 config/

# Log files
chmod 644 logs/*.log
```

### Network Security

- Use HTTPS for web interfaces
- Implement proper authentication
- Restrict file upload sizes
- Validate all input files

### Container Security

```dockerfile
# Use non-root user
USER appuser

# Read-only root filesystem
--read-only --tmpfs /tmp

# Drop capabilities
--cap-drop=ALL
```

## Backup and Recovery

### Configuration Backup

```bash
# Backup configuration
cp config.json config.json.backup.$(date +%Y%m%d)

# Backup entire installation
tar -czf tiktok-processor-backup-$(date +%Y%m%d).tar.gz \
  /path/to/installation/
```

### Database Backup (if applicable)

```bash
# Backup video cache
cp video_cache.json video_cache.json.backup
```

### Recovery Procedures

1. **Stop application**
2. **Restore from backup**
3. **Validate configuration**
4. **Restart application**

## Troubleshooting

### Common Issues

#### FFmpeg Not Found

```bash
# Check FFmpeg installation
which ffmpeg
ffmpeg -version

# Install FFmpeg
# Ubuntu: sudo apt-get install ffmpeg
# macOS: brew install ffmpeg
# Windows: Download from https://ffmpeg.org
```

#### Permission Denied

```bash
# Fix permissions
chmod +x scripts/deploy_*.sh
chown -R $USER:$USER /path/to/installation/
```

#### Python Module Not Found

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

#### Configuration Issues

```bash
# Validate configuration
python main.py --validate-config

# Reset configuration
python main.py --create-config
```

### Debug Mode

Enable debug logging:

```bash
python main.py --debug --cli list
```

### Log Analysis

```bash
# View recent logs
tail -f logs/app_$(date +%Y%m%d).log

# Search for errors
grep -i error logs/*.log

# Monitor processing
grep -i "processing" logs/*.log
```

## Performance Tuning

### Configuration Optimization

```json
{
  "performance": {
    "max_workers": 4,
    "cache_enabled": true,
    "memory_limit_mb": 2048
  },
  "video": {
    "crf_value": 23
  },
  "ffmpeg": {
    "preset": "fast"
  }
}
```

### System Optimization

```bash
# Increase file descriptor limits
ulimit -n 4096

# Optimize for video processing
echo 'vm.swappiness=10' >> /etc/sysctl.conf
echo 'vm.vfs_cache_pressure=50' >> /etc/sysctl.conf
```

## Scaling

### Horizontal Scaling

Use multiple instances with shared storage:

```yaml
# docker-compose.yml
version: "3.8"
services:
  processor-1:
    image: tiktok-video-processor
    volumes:
      - shared-input:/app/input
      - shared-output:/app/output

  processor-2:
    image: tiktok-video-processor
    volumes:
      - shared-input:/app/input
      - shared-output:/app/output

volumes:
  shared-input:
  shared-output:
```

### Load Balancing

Use nginx for load balancing:

```nginx
upstream processors {
    server processor-1:8000;
    server processor-2:8000;
}

server {
    location / {
        proxy_pass http://processors;
    }
}
```

---

For additional deployment assistance, please refer to the troubleshooting section or create an issue with your specific deployment scenario.
