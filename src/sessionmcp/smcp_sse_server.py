"""Enhanced SSE server with session parameter support.

This module extends the standard SSE server implementation to store and provide 
access to query parameters from the initial connection.
"""

import logging
from dataclasses import dataclass
from typing import Dict, Any, List, Literal, Optional
from uuid import UUID

import uvicorn
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.routing import Mount, Route
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.server import Server

from .session_sse_transport import ExtendedSseServerTransport
from .session_context import SessionContext

logger = logging.getLogger(__name__)


@dataclass
class EnhancedSseServerSettings:
    """Settings for the enhanced SSE server."""

    bind_host: str
    port: int
    allow_origins: Optional[List[str]] = None
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"


# Global registry to store session contexts
SESSION_REGISTRY: Dict[UUID, SessionContext] = {}


def create_enhanced_starlette_app(
    mcp_server: Server,
    *,
    allow_origins: Optional[List[str]] = None,
    debug: bool = False,
) -> Starlette:
    """Create a Starlette application that uses the enhanced SSE transport."""
    # Use our extended SSE transport instead of the standard one
    sse = ExtendedSseServerTransport("/messages/")
    
    async def handle_sse(request: Request) -> None:
        async with sse.connect_sse(
            request.scope,
            request.receive,
            request._send,  # noqa: SLF001
        ) as (read_stream, write_stream):
            # Find the session ID that was just created
            session_id = None
            for sid, writer in sse._read_stream_writers.items():
                # The most recently added session is the one we want
                session_id = sid
                break
            
            if session_id:
                # Create and store session context
                session_ctx = SessionContext(session_id=session_id, transport=sse)
                SESSION_REGISTRY[session_id] = session_ctx
                logger.debug(f"Registered session context for ID {session_id}")
            
            # Run the MCP server with this session
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )
            
            # Clean up after the session ends
            if session_id and session_id in SESSION_REGISTRY:
                del SESSION_REGISTRY[session_id]
                logger.debug(f"Removed session context for ID {session_id}")

    middleware: List[Middleware] = []
    if allow_origins is not None:
        middleware.append(
            Middleware(
                CORSMiddleware,
                allow_origins=allow_origins,
                allow_methods=["*"],
                allow_headers=["*"],
            ),
        )

    return Starlette(
        debug=debug,
        middleware=middleware,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )


async def run_enhanced_sse_server(
    stdio_params: StdioServerParameters,
    sse_settings: EnhancedSseServerSettings,
) -> None:
    """Run the enhanced stdio client with SSE server.

    Args:
        stdio_params: The parameters for the stdio client.
        sse_settings: The settings for the enhanced SSE server.
    """
    from .proxy_server import create_proxy_server
    
    async with stdio_client(stdio_params) as streams, ClientSession(*streams) as session:
        mcp_server = await create_proxy_server(session)

        # Attach a method to get the session context
        def get_session_context_for_message(message_id: str) -> Optional[SessionContext]:
            """Get the session context associated with a message."""
            # In a real implementation, we would extract the session ID from the message
            # and look it up in the registry. For now, we'll return the first one we find.
            if SESSION_REGISTRY:
                return next(iter(SESSION_REGISTRY.values()))
            return None
        
        # Attach the method to the server for tool implementations to use
        mcp_server.get_session_context = get_session_context_for_message

        # Create the Starlette app with our enhanced configuration
        starlette_app = create_enhanced_starlette_app(
            mcp_server,
            allow_origins=sse_settings.allow_origins,
            debug=(sse_settings.log_level == "DEBUG"),
        )

        # Configure and run the HTTP server
        config = uvicorn.Config(
            starlette_app,
            host=sse_settings.bind_host,
            port=sse_settings.port,
            log_level=sse_settings.log_level.lower(),
        )
        http_server = uvicorn.Server(config)
        await http_server.serve() 