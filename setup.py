"""
Setup configuration for Abiqua Asset Management.

Allows package to be installed in development mode: pip install -e .

References:
- Repo & Coding Standards (#17)
"""

from setuptools import find_packages, setup

setup(
    name="abiqua-asset-management",
    version="0.1.0",
    description="Abiqua Asset Management - Secure messaging system",
    author="Abiqua Team",
    packages=find_packages(exclude=["tests", "tests.*"]),
    python_requires=">=3.8",
    install_requires=[
        # Core dependencies will be added as modules are implemented
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0,<8.0.0",
            "pytest-cov>=4.0.0,<5.0.0",
            "pytest-mock>=3.10.0,<4.0.0",
            "black>=23.0.0,<24.0.0",
            "flake8>=6.0.0,<7.0.0",
            "mypy>=1.0.0,<2.0.0",
            "isort>=5.12.0,<6.0.0",
            "types-mock>=1.0.0",
        ],
    },
    zip_safe=False,
)
