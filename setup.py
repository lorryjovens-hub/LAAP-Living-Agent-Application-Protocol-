"""LAAP — Lifeform Autonomous Adaptive Protocol"""
from setuptools import setup, find_packages

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="laap",
    version="0.3.3",
    description="LAAP - Lifeform Autonomous Adaptive Protocol (自进化引擎意识生命体)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="LAAP Team",
    url="https://github.com/laap-agi/laap",
    packages=find_packages(include=["laap", "laap.*"]),
    install_requires=[
        "numpy>=1.24.0",
        "pydantic>=2.0.0",
    ],
    extras_require={
        "openai": ["openai>=1.0.0"],
        "anthropic": ["anthropic>=0.30.0"],
        "deepseek": ["openai>=1.0.0"],
        "ollama": ["httpx>=0.27.0"],
        "api": ["fastapi>=0.104.0", "uvicorn>=0.24.0"],
        "dev": ["pytest>=7.4.0"],
        "all": [
            "openai>=1.0.0", "anthropic>=0.30.0",
            "httpx>=0.27.0", "fastapi>=0.104.0",
            "uvicorn>=0.24.0", "pytest>=7.4.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "laap=laap.api.cli:main",
        ],
    },
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Build Tools",
    ],
)
