"""Session context module to provide access to session parameters.

This module provides a context class that allows tool implementations to 
access the query parameters from the initial SSE connection.
"""

import logging
from typing import Dict, Any, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class SessionContext:
    """Context providing access to session parameters and metadata."""
    
    def __init__(self, session_id: Optional[UUID] = None, transport: Any = None):
        """Initialize session context with session ID and transport reference."""
        self._session_id = session_id
        self._transport = transport
    
    @property
    def session_id(self) -> Optional[UUID]:
        """Get the session ID."""
        return self._session_id
    
    def get_session_params(self) -> Dict[str, Any]:
        """Get the query parameters associated with this session."""
        if not self._session_id or not self._transport:
            logger.debug("No session ID or transport available for parameter access")
            return {}
        
        # Check if the transport has the get_session_params method
        if hasattr(self._transport, "get_session_params"):
            params = self._transport.get_session_params(self._session_id)
            logger.debug(f"Retrieved session parameters: {params}")
            return params
        
        logger.debug("Transport does not support session parameters")
        return {}
    
    def get_param(self, key: str, default: Any = None) -> Any:
        """Get a specific parameter value by key."""
        params = self.get_session_params()
        return params.get(key, default) 