"""Enhanced proxy server that provides access to session parameters.

This module extends the standard proxy server to provide access to the 
query parameters from the initial SSE connection in tool implementations.
"""

import logging
import typing as t
from uuid import UUID

from mcp import server, types
from mcp.client.session import ClientSession
from mcp.shared.context import RequestContext

from .session_context import SessionContext

logger = logging.getLogger(__name__)

# Type alias for the function to get session context
GetSessionContextFunc = t.Callable[[str], t.Optional[SessionContext]]


class EnhancedServer(server.Server):
    """Enhanced MCP server with session parameter access."""
    
    def __init__(self, name: str, version: str = "0.1.0"):
        """Initialize the enhanced server."""
        super().__init__(name, version)
        # Function to get session context, to be set externally
        self.get_session_context: GetSessionContextFunc = lambda _: None
    
    def get_session_params_for_request(self, request_id: str) -> t.Dict[str, t.Any]:
        """Get session parameters for a request ID."""
        ctx = self.get_session_context(request_id)
        if ctx:
            return ctx.get_session_params()
        return {}


async def create_enhanced_proxy_server(
    remote_app: ClientSession,
    get_session_context: t.Optional[GetSessionContextFunc] = None,
) -> EnhancedServer:
    """Create an enhanced server instance from a remote app.
    
    Args:
        remote_app: The remote client session to proxy requests through
        get_session_context: Optional function to get session context for a request
        
    Returns:
        An enhanced server instance with session parameter access
    """
    response = await remote_app.initialize()
    capabilities = response.capabilities

    app = EnhancedServer(response.serverInfo.name)
    
    # Set the function to get session context if provided
    if get_session_context:
        app.get_session_context = get_session_context

    # Modify the call_tool handler to include session parameters
    if capabilities.tools:

        async def _list_tools(_: t.Any) -> types.ServerResult:  # noqa: ANN401
            tools = await remote_app.list_tools()
            return types.ServerResult(tools)

        app.request_handlers[types.ListToolsRequest] = _list_tools

        async def _call_tool(req: types.CallToolRequest) -> types.ServerResult:
            try:
                # Get the request context
                request_ctx = app.request_context
                request_id = str(request_ctx.request_id) if request_ctx else None
                
                # Get session parameters for this request
                session_params = {}
                if request_id:
                    session_ctx = app.get_session_context(request_id)
                    if session_ctx:
                        session_params = session_ctx.get_session_params()
                        logger.debug(f"Found session params for request {request_id}: {session_params}")
                
                # Add session parameters to tool arguments if needed
                arguments = (req.params.arguments or {}).copy()
                if session_params:
                    # You could pass the session_params directly or handle them in a way specific to your needs
                    # For example, you might add them under a special key:
                    arguments["_session_params"] = session_params
                    
                    # Or extract specific parameters as needed by the tool:
                    if "auth" in session_params:
                        arguments["api_key"] = session_params["auth"]
                
                result = await remote_app.call_tool(
                    req.params.name,
                    arguments,
                )
                return types.ServerResult(result)
            except Exception as e:  # noqa: BLE001
                logger.exception("Error calling tool")
                return types.ServerResult(
                    types.CallToolResult(
                        content=[types.TextContent(type="text", text=str(e))],
                        isError=True,
                    ),
                )

        app.request_handlers[types.CallToolRequest] = _call_tool

    # Add the rest of the handlers (same as in the original proxy_server.py)
    # For brevity, I'm only showing the modified tool handler above

    return app 