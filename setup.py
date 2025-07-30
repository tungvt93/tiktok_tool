#!/usr/bin/env python3
"""
Setup script for TikTok Video Processing Tool
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_path.exists():
    with open(requirements_path, 'r', encoding='utf-8') as f:
        requirements = [
            line.strip()
            for line in f
            if line.strip() and not line.startswith('#') and not line.startswith('-')
        ]

setup(
    name="tiktok-video-processor",
    version="2.0.0",
    author="TikTok Video Processing Team",
    author_email="developer@example.com",
    description="A professional video processing tool for creating TikTok-style videos with effects",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/example/tiktok-video-processor",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Video",
        "Topic :: Multimedia :: Video :: Conversion",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-mock>=3.10.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=1.0.0",
            "coverage>=7.0.0",
        ],
        "gui": [
            # tkinter is usually included with Python
            # Add any additional GUI dependencies here
        ],
    },
    entry_points={
        "console_scripts": [
            "tiktok-processor=main:main",
            "tiktok-video-tool=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.json", "*.md", "*.txt"],
    },
    data_files=[
        ("config", ["config/default.json"]),
        ("docs", ["docs/DEVELOPER_GUIDE.md"]),
    ],
    project_urls={
        "Bug Reports": "https://github.com/example/tiktok-video-processor/issues",
        "Source": "https://github.com/example/tiktok-video-processor",
        "Documentation": "https://github.com/example/tiktok-video-processor/blob/main/README.md",
    },
    keywords="video processing tiktok effects ffmpeg clean-architecture",
    zip_safe=False,
)
