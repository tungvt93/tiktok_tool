#!/usr/bin/env python3
"""
Setup script for TikTok Video Processing Tool

Clean Architecture Edition with GPU acceleration and performance monitoring.
"""

from setuptools import setup, find_packages
import os

# Read the README file
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "TikTok Video Processing Tool - Clean Architecture Edition"

# Read requirements
def read_requirements():
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if os.path.exists(requirements_path):
        with open(requirements_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return []

setup(
    name="tiktok-video-tool",
    version="2.0.0",
    author="TikTok Tool Team",
    author_email="team@tiktoktool.com",
    description="Advanced TikTok video processing tool with GPU acceleration and clean architecture",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/tungvt93/tiktok_tool",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Video",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Utilities",
    ],
    python_requires=">=3.8",
    install_requires=[
        # Core dependencies
        "pathlib2>=2.3.7;python_version<'3.4'",
        "typing-extensions>=4.0.0",
        
        # Video processing
        "opencv-python>=4.8.0",
        "Pillow>=10.0.0",
        "numpy>=1.24.0",
        
        # Performance monitoring
        "psutil>=5.9.0",
        "memory-profiler>=0.61.0",
        
        # Configuration and utilities
        "pyyaml>=6.0",
        "click>=8.1.0",
        "rich>=13.0.0",
        
        # Logging and monitoring
        "structlog>=23.0.0",
        "colorama>=0.4.6",
        
        # GUI (optional)
        "tkinter-tooltip>=2.0.0",
        
        # Testing
        "pytest>=7.0.0",
        "pytest-cov>=4.0.0",
        "pytest-mock>=3.10.0",
        
        # Development tools
        "black>=23.0.0",
        "flake8>=6.0.0",
        "mypy>=1.0.0",
        "pre-commit>=3.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-mock>=3.10.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            "pre-commit>=3.0.0",
            "tox>=4.0.0",
        ],
        "gpu": [
            "torch>=2.0.0",
            "torchvision>=0.15.0",
            "cupy-cuda11x>=12.0.0;platform_system=='Linux'",
            "cupy-cuda12x>=12.0.0;platform_system=='Linux'",
        ],
        "monitoring": [
            "prometheus-client>=0.17.0",
            "grafana-api>=1.0.3",
            "influxdb-client>=1.36.0",
        ],
        "gui": [
            "tkinter-tooltip>=2.0.0",
            "tkinterdnd2>=0.3.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "tiktok-tool=main:main",
            "tiktok-gui=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.json", "*.yaml", "*.yml", "*.md", "*.txt"],
        "src": ["**/*.json", "**/*.yaml", "**/*.yml"],
    },
    keywords=[
        "tiktok",
        "video",
        "processing",
        "ffmpeg",
        "gpu",
        "acceleration",
        "clean-architecture",
        "performance",
        "monitoring",
    ],
    project_urls={
        "Bug Reports": "https://github.com/tungvt93/tiktok_tool/issues",
        "Source": "https://github.com/tungvt93/tiktok_tool",
        "Documentation": "https://github.com/tungvt93/tiktok_tool/blob/main/README.md",
    },
)
