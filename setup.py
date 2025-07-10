#!/usr/bin/env python3
"""
Setup script for video-extract - AI-powered YouTube video transcript and slide analyzer
"""

from setuptools import setup, find_packages
import os

# Read the README file for long description
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Read requirements from requirements.txt
def read_requirements():
    requirements = []
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("pytest") and not line.startswith("black") and not line.startswith("flake8") and not line.startswith("mypy"):
                requirements.append(line)
    return requirements

setup(
    name="video-extract",
    version="1.0.1",
    author="Philipp",
    author_email="",
    description="AI-powered YouTube video transcript and slide analyzer",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/your-username/video-extract",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Video",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Text Processing :: Linguistic",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.7.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "video-extract=src.cli:main",
            "vext=src.cli:main",  # shorter alias
        ],
    },
    include_package_data=True,
    package_data={
        "src": ["*.example"],
    },
    keywords="youtube, transcript, ai, video, slides, openai, gpt, ocr, analysis",
    project_urls={
        "Bug Reports": "https://github.com/your-username/video-extract/issues",
        "Source": "https://github.com/your-username/video-extract",
        "Documentation": "https://github.com/your-username/video-extract#readme",
    },
)