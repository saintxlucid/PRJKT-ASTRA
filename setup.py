# ASTRA Test Suite Setup
# Created: October 16, 2025

from setuptools import setup, find_packages

setup(
    name="astra",
    version="2.5.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.10",
    install_requires=[
        "aiohttp>=3.8.0",
        "fastapi>=0.100.0",
        "pydantic>=2.0.0",
        "sqlalchemy>=2.0.0",
        "structlog>=23.1.0",
        "torch>=2.0.0",
        "transformers>=4.30.0",
        "pytest>=7.0.0",
        "pytest-asyncio>=0.21.0",
        "pytest-cov>=4.1.0",
        "numpy>=1.22.0",
        "pdfminer.six>=20221105",
        "pdfplumber>=0.10.0",
        "sentence-transformers>=2.2.0",
        "qdrant-client>=1.7.0"
    ]
)