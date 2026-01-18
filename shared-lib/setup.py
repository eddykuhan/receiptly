"""
Receiptly Core - Shared canonicalization library for receipt processing and retail ETL.
"""
from setuptools import setup, find_packages

setup(
    name="receiptly-core",
    version="0.1.0",
    description="Shared product canonicalization library for Receiptly",
    author="Receiptly Team",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "fuzzywuzzy>=0.18.0",
        "python-Levenshtein>=0.21.0",
        "numpy>=1.24.0",
    ],
    extras_require={
        "embeddings": [
            "sentence-transformers>=2.2.0",
            "torch>=2.0.0",
        ],
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
        ]
    },
)
