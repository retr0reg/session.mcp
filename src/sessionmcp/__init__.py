"""MCP proxy package.

Provides a proxy for MCP connections with enhanced features like session parameter access.
"""

from .smcp_sse_server import (
    EnhancedSseServerSettings, 
    create_enhanced_starlette_app, 
    run_enhanced_sse_server,
)
from .session_context import SessionContext
from .session_sse_transport import ExtendedSseServerTransport
from .session_utils import (
    extract_session_param,
    prepare_tool_arguments,
)

__all__ = [
    "EnhancedSseServerSettings",
    "SessionContext",
    "ExtendedSseServerTransport",
    "create_enhanced_starlette_app",
    "run_enhanced_sse_server",
    "extract_session_param",
    "prepare_tool_arguments",
]
