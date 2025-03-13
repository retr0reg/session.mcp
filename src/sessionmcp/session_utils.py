"""Utility module for session parameter access.

This module provides helper functions for tool implementations to
access query parameters from the initial SSE connection.
"""

import logging
import typing as t
from contextlib import contextmanager

from mcp.server.fastmcp import Context

logger = logging.getLogger(__name__)


def extract_session_param(
    param_name: str, 
    arguments: t.Dict[str, t.Any], 
    default: t.Any = None
) -> t.Any:
    """Extract a session parameter from the arguments.
    
    Args:
        param_name: The name of the parameter to extract
        arguments: The tool arguments dictionary
        default: The default value to return if the parameter is not found
        
    Returns:
        The parameter value if found, otherwise the default value
    """
    session_params = arguments.get("_session_params", {})
    if session_params and param_name in session_params:
        return session_params[param_name]
    return default


@contextmanager
def prepare_tool_arguments(arguments: t.Dict[str, t.Any]) -> t.Iterator[t.Dict[str, t.Any]]:
    """Context manager to prepare tool arguments with session parameters.
    
    This function cleans up the arguments dictionary by removing the _session_params
    key before yielding, and restores it afterward.
    
    Args:
        arguments: The tool arguments dictionary
        
    Yields:
        A copy of the arguments dictionary with _session_params removed
    """
    # Make a copy of the arguments
    args_copy = arguments.copy()
    session_params = args_copy.pop("_session_params", {})
    
    try:
        # Yield the cleaned arguments
        yield args_copy
    finally:
        # Restore the session parameters if they existed
        if session_params:
            arguments["_session_params"] = session_params 