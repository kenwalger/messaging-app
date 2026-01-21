"""
Controller authentication service for Abiqua Asset Management.

References:
- API Contracts (#10), Section 5
- Identity Provisioning (#11)
- Resolved Specs & Clarifications

Implements simple API key-based authentication for controller operations.
Per API Contracts (#10), Section 5: controller authentication via X-Controller-Key header.
"""

import logging
from typing import Optional

from src.shared.constants import HEADER_CONTROLLER_KEY

# Configure logging per Logging & Observability (#14)
logger = logging.getLogger(__name__)


class ControllerAuthService:
    """
    Controller authentication service per API Contracts (#10), Section 5.
    
    Validates controller authorization using API key.
    Simple implementation for now (can be enhanced with token-based auth later).
    """
    
    def __init__(self, valid_api_keys: Optional[list[str]] = None) -> None:
        """
        Initialize controller authentication service.
        
        Args:
            valid_api_keys: List of valid API keys. If None, uses default test key.
                           In production, this would come from secure configuration.
        """
        # Default test key for development
        # In production, this would be loaded from secure configuration
        self._valid_keys: set[str] = set(valid_api_keys or ["test-controller-key"])
    
    def validate_controller_key(self, api_key: Optional[str]) -> bool:
        """
        Validate controller API key per API Contracts (#10), Section 5.
        
        Args:
            api_key: API key from X-Controller-Key header.
        
        Returns:
            True if API key is valid, False otherwise.
        """
        if not api_key:
            logger.warning("Controller request missing API key")
            return False
        
        is_valid = api_key in self._valid_keys
        
        if not is_valid:
            logger.warning(f"Invalid controller API key attempted")
        
        return is_valid
    
    def add_valid_key(self, api_key: str) -> None:
        """
        Add a valid API key (for testing or dynamic key management).
        
        Args:
            api_key: API key to add.
        """
        self._valid_keys.add(api_key)
        logger.debug(f"Added controller API key")
    
    def remove_valid_key(self, api_key: str) -> None:
        """
        Remove a valid API key.
        
        Args:
            api_key: API key to remove.
        """
        self._valid_keys.discard(api_key)
        logger.debug(f"Removed controller API key")
