#!/usr/bin/env python3
"""
Build Script

Automated build script for creating distribution packages.
"""

import sys
import subprocess
import shutil
import tempfile
from pathlib import Path
import argparse
import logging
import json
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class BuildManager:
    """Manages the build process for different platforms"""

    def __init__(self, project_root: Path = None):
        """
        Initialize build manager.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = project_root or Path(__file__).parent.parent
        self.dist_dir = self.project_root / "dist"
        self.build_dir = self.project_root / "build"
        self.version = self._get_version()

    def _get_version(self) -> str:
        """Get version from setup.py"""
        try:
            setup_py = self.project_root / "setup.py"
            if setup_py.exists():
                content = setup_py.read_text()
                for line in content.split('\n'):
                    if 'version=' in line and '"' in line:
                        return line.split('"')[1]
            return "2.0.0"
        except Exception:
            return "2.0.0"

    def clean_build_dirs(self):
        """Clean build and dist directories"""
        logger.info("Cleaning build directories...")

        dirs_to_clean = [self.dist_dir, self.build_dir]
        for dir_path in dirs_to_clean:
            if dir_path.exists():
                shutil.rmtree(dir_path)
                logger.info(f"Cleaned {dir_path}")

        # Clean __pycache__ directories
        for pycache in self.project_root.rglob("__pycache__"):
            shutil.rmtree(pycache)

        # Clean .pyc files
        for pyc_file in self.project_root.rglob("*.pyc"):
            pyc_file.unlink()

    def validate_environment(self) -> bool:
        """Validate build environment"""
        logger.info("Validating build environment...")

        # Check Python version
        if sys.version_info < (3, 8):
            logger.error("Python 3.8 or higher is required")
            return False

        # Check required files exist
        required_files = [
            "setup.py",
            "README.md",
            "requirements.txt",
            "main.py",
            "src/__init__.py"
        ]

        for file_path in required_files:
            if not (self.project_root / file_path).exists():
                logger.error(f"Required file missing: {file_path}")
                return False

        # Check setuptools is available
        try:
            import setuptools
            logger.info(f"Using setuptools {setuptools.__version__}")
        except ImportError:
            logger.error("setuptools is required for building")
            return False

        # Check wheel is available
        try:
            import wheel
            logger.info(f"Using wheel {wheel.__version__}")
        except ImportError:
            logger.warning("wheel not available - only source distribution will be built")

        logger.info("Build environment validation passed")
        return True

    def run_tests(self) -> bool:
        """Run tests before building"""
        logger.info("Running tests...")

        try:
            # Run our custom test suites
            test_scripts = [
                "test_compatibility.py",
                "test_migration_simple.py",
                "test_output_quality.py"
            ]

            for test_script in test_scripts:
                test_path = self.project_root / test_script
                if test_path.exists():
                    logger.info(f"Running {test_script}...")
                    result = subprocess.run([sys.executable, str(test_path)],
                                          capture_output=True, text=True)

                    if result.returncode != 0:
                        logger.error(f"Test {test_script} failed:")
                        logger.error(result.stdout)
                        logger.error(result.stderr)
                        return False

                    logger.info(f"✓ {test_script} passed")

            # Run migration validation
            validate_script = self.project_root / "validate_migration.py"
            if validate_script.exists():
                logger.info("Running migration validation...")
                result = subprocess.run([sys.executable, str(validate_script)],
                                      capture_output=True, text=True)

                if result.returncode != 0:
                    logger.error("Migration validation failed:")
                    logger.error(result.stdout)
                    logger.error(result.stderr)
                    return False

                logger.info("✓ Migration validation passed")

            logger.info("All tests passed")
            return True

        except Exception as e:
            logger.error(f"Error running tests: {e}")
            return False

    def build_source_distribution(self) -> bool:
        """Build source distribution"""
        logger.info("Building source distribution...")

        try:
            result = subprocess.run([
                sys.executable, "setup.py", "sdist"
            ], cwd=self.project_root, capture_output=True, text=True)

            if result.returncode != 0:
                logger.error("Source distribution build failed:")
                logger.error(result.stderr)
                return False

            logger.info("✓ Source distribution built successfully")
            return True

        except Exception as e:
            logger.error(f"Error building source distribution: {e}")
            return False

    def build_wheel_distribution(self) -> bool:
        """Build wheel distribution"""
        logger.info("Building wheel distribution...")

        try:
            result = subprocess.run([
                sys.executable, "setup.py", "bdist_wheel"
            ], cwd=self.project_root, capture_output=True, text=True)

            if result.returncode != 0:
                logger.error("Wheel distribution build failed:")
                logger.error(result.stderr)
                return False

            logger.info("✓ Wheel distribution built successfully")
            return True

        except Exception as e:
            logger.error(f"Error building wheel distribution: {e}")
            return False

    def create_standalone_package(self) -> bool:
        """Create standalone package with all dependencies"""
        logger.info("Creating standalone package...")

        try:
            # Create standalone directory
            standalone_dir = self.dist_dir / f"tiktok-video-processor-{self.version}-standalone"
            standalone_dir.mkdir(parents=True, exist_ok=True)

            # Copy source code
            src_files = [
                "main.py",
                "src/",
                "config/",
                "README.md",
                "requirements.txt",
                "CHANGELOG.md"
            ]

            for src_file in src_files:
                src_path = self.project_root / src_file
                if src_path.exists():
                    if src_path.is_dir():
                        shutil.copytree(src_path, standalone_dir / src_file,
                                      ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
                    else:
                        shutil.copy2(src_path, standalone_dir / src_file)

            # Create run script
            run_script = standalone_dir / "run.py"
            run_script.write_text('''#!/usr/bin/env python3
"""
Standalone runner for TikTok Video Processing Tool
"""

import sys
from pathlib import Path

# Add src directory to path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

# Import and run main
from main import main

if __name__ == "__main__":
    sys.exit(main())
''')

            # Make run script executable
            run_script.chmod(0o755)

            # Create batch file for Windows
            batch_script = standalone_dir / "run.bat"
            batch_script.write_text('''@echo off
python run.py %*
''')

            # Create shell script for Unix
            shell_script = standalone_dir / "run.sh"
            shell_script.write_text('''#!/bin/bash
python3 run.py "$@"
''')
            shell_script.chmod(0o755)

            # Create installation instructions
            install_readme = standalone_dir / "INSTALL.md"
            install_readme.write_text(f'''# TikTok Video Processing Tool v{self.version} - Standalone Package

## Installation

1. Extract this package to your desired location
2. Install Python 3.8 or higher
3. Install FFmpeg and ensure it's in your PATH
4. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Windows
```
run.bat --help
```

### macOS/Linux
```
./run.sh --help
```

### Direct Python
```
python run.py --help
```

## Examples

```bash
# GUI mode
./run.sh

# CLI mode - list videos
./run.sh --cli list

# CLI mode - process video
./run.sh --cli process input.mp4 background.mp4 -o output.mp4 -e fade_in
```

For more information, see README.md
''')

            logger.info(f"✓ Standalone package created: {standalone_dir}")
            return True

        except Exception as e:
            logger.error(f"Error creating standalone package: {e}")
            return False

    def create_docker_image(self) -> bool:
        """Create Docker image"""
        logger.info("Creating Docker image...")

        try:
            # Create Dockerfile
            dockerfile_content = f'''FROM python:3.9-slim

# Install FFmpeg
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port (if needed for future web interface)
EXPOSE 8000

# Default command
CMD ["python", "main.py", "--help"]
'''

            dockerfile_path = self.project_root / "Dockerfile"
            dockerfile_path.write_text(dockerfile_content)

            # Create .dockerignore
            dockerignore_content = '''__pycache__
*.pyc
*.pyo
*.pyd
.git
.gitignore
README.md
Dockerfile
.dockerignore
dist/
build/
*.egg-info/
.pytest_cache/
.coverage
.tox/
venv/
env/
'''

            dockerignore_path = self.project_root / ".dockerignore"
            dockerignore_path.write_text(dockerignore_content)

            # Build Docker image
            image_name = f"tiktok-video-processor:{self.version}"

            result = subprocess.run([
                "docker", "build", "-t", image_name, "."
            ], cwd=self.project_root, capture_output=True, text=True)

            if result.returncode != 0:
                logger.error("Docker image build failed:")
                logger.error(result.stderr)
                return False

            logger.info(f"✓ Docker image built: {image_name}")

            # Create docker-compose.yml for easy deployment
            compose_content = f'''version: '3.8'

services:
  tiktok-processor:
    image: {image_name}
    container_name: tiktok-video-processor
    volumes:
      - ./input:/app/input
      - ./output:/app/output
      - ./config:/app/config
    environment:
      - LOG_LEVEL=INFO
    command: python main.py --cli list

  # Example service for batch processing
  batch-processor:
    image: {image_name}
    container_name: tiktok-batch-processor
    volumes:
      - ./input:/app/input
      - ./output:/app/output
      - ./config:/app/config
    environment:
      - LOG_LEVEL=INFO
    profiles:
      - batch
    command: python main.py --cli process input/video.mp4 input/background.mp4 -o output/result.mp4
'''

            compose_path = self.project_root / "docker-compose.yml"
            compose_path.write_text(compose_content)

            logger.info("✓ Docker Compose file created")
            return True

        except Exception as e:
            logger.error(f"Error creating Docker image: {e}")
            return False

    def generate_build_info(self) -> bool:
        """Generate build information file"""
        logger.info("Generating build information...")

        try:
            import datetime
            import platform

            build_info = {
                "version": self.version,
                "build_date": datetime.datetime.now().isoformat(),
                "python_version": sys.version,
                "platform": platform.platform(),
                "architecture": platform.architecture()[0],
                "build_system": {
                    "os": platform.system(),
                    "release": platform.release(),
                    "machine": platform.machine()
                }
            }

            build_info_path = self.dist_dir / "build_info.json"
            build_info_path.parent.mkdir(parents=True, exist_ok=True)

            with open(build_info_path, 'w') as f:
                json.dump(build_info, f, indent=2)

            logger.info(f"✓ Build information saved: {build_info_path}")
            return True

        except Exception as e:
            logger.error(f"Error generating build info: {e}")
            return False

    def build_all(self, skip_tests: bool = False, skip_docker: bool = False) -> bool:
        """Build all distribution packages"""
        logger.info(f"Starting build process for version {self.version}")

        # Validate environment
        if not self.validate_environment():
            return False

        # Clean build directories
        self.clean_build_dirs()

        # Run tests
        if not skip_tests and not self.run_tests():
            logger.error("Tests failed - aborting build")
            return False

        # Build distributions
        success = True

        if not self.build_source_distribution():
            success = False

        if not self.build_wheel_distribution():
            success = False

        if not self.create_standalone_package():
            success = False

        if not skip_docker and not self.create_docker_image():
            logger.warning("Docker image creation failed - continuing with other builds")

        if not self.generate_build_info():
            success = False

        if success:
            logger.info("🎉 Build completed successfully!")
            self._print_build_summary()
        else:
            logger.error("❌ Build completed with errors")

        return success

    def _print_build_summary(self):
        """Print build summary"""
        print("\n" + "=" * 50)
        print("BUILD SUMMARY")
        print("=" * 50)

        if self.dist_dir.exists():
            print(f"Distribution files created in: {self.dist_dir}")
            for file_path in self.dist_dir.iterdir():
                if file_path.is_file():
                    size = file_path.stat().st_size
                    size_str = f"{size:,} bytes"
                    print(f"  📦 {file_path.name} ({size_str})")
                elif file_path.is_dir():
                    print(f"  📁 {file_path.name}/")

        print("\nNext steps:")
        print("1. Test the built packages")
        print("2. Upload to package repository (if desired)")
        print("3. Create release notes")
        print("4. Tag the release in version control")


def main():
    """Main build script entry point"""
    parser = argparse.ArgumentParser(
        description="Build TikTok Video Processing Tool distributions"
    )

    parser.add_argument(
        '--skip-tests', action='store_true',
        help='Skip running tests before building'
    )

    parser.add_argument(
        '--skip-docker', action='store_true',
        help='Skip Docker image creation'
    )

    parser.add_argument(
        '--clean-only', action='store_true',
        help='Only clean build directories'
    )

    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create build manager
    builder = BuildManager()

    # Clean only mode
    if args.clean_only:
        builder.clean_build_dirs()
        print("Build directories cleaned")
        return 0

    # Build all packages
    success = builder.build_all(
        skip_tests=args.skip_tests,
        skip_docker=args.skip_docker
    )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
