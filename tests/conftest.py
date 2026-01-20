"""
Pytest configuration for Abiqua Asset Management tests.

Adds project root to Python path to enable imports.
References:
- Repo & Coding Standards (#17)
"""

import sys
from pathlib import Path

# Add project root to Python path
# This ensures imports from src.* work correctly
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def pytest_configure(config):
    """
    Pytest configuration hook.
    
    Ensures project root is in Python path before any imports.
    """
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
