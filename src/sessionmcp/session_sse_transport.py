"""Extended SSE transport with session parameter support.

This module extends the standard SseServerTransport to store query parameters
from the initial connection and make them available to tool implementations.
"""

import logging
from typing import Dict, Any, Tuple, AsyncContextManager
from urllib.parse import parse_qs
from uuid import UUID
from contextlib import asynccontextmanager

import anyio
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from mcp.server.sse import SseServerTransport
from mcp.types import JSONRPCMessage
from starlette.types import Scope, Receive, Send

logger = logging.getLogger(__name__)


class ExtendedSseServerTransport(SseServerTransport):
    """
    Extended SSE server transport that stores query parameters from the initial connection.
    """

    def __init__(self, endpoint: str) -> None:
        """Create a new extended SSE server transport."""
        super().__init__(endpoint)
        self._session_params: Dict[UUID, Dict[str, Any]] = {}
        logger.debug("ExtendedSseServerTransport initialized with parameter storage")

    @asynccontextmanager
    async def connect_sse(
        self, scope: Scope, receive: Receive, send: Send
    ) -> AsyncContextManager[Tuple[MemoryObjectReceiveStream, MemoryObjectSendStream]]:
        """Connect to SSE and store query parameters."""
        # Extract query parameters from scope
        query_string = scope.get("query_string", b"").decode("utf-8")
        query_params = {}
        
        if query_string:
            # Parse query string into dictionary
            parsed_qs = parse_qs(query_string)
            # Convert lists to single values for easier access
            query_params = {k: v[0] if len(v) == 1 else v for k, v in parsed_qs.items()}
            logger.debug(f"Extracted query parameters: {query_params}")
        
        # Use the parent's connect_sse - properly handle the context manager
        async with super().connect_sse(scope, receive, send) as streams:
            # Find the session_id that was just created
            session_id = None
            for sid, writer in self._read_stream_writers.items():
                # Check the last added session (the one we just created)
                session_id = sid
                break
            
            if session_id:
                # Store the query parameters with the session ID
                self._session_params[session_id] = query_params
                logger.debug(f"Associated parameters with session ID {session_id}")
            
            # Properly yield and return from the context manager
            yield streams

    def get_session_params(self, session_id: UUID) -> Dict[str, Any]:
        """Get query parameters associated with a session ID."""
        return self._session_params.get(session_id, {}) 