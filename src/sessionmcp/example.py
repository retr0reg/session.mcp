"""Example of using session parameters in an MCP tool.

This example shows how to set up an enhanced SSE server and access
the query parameters from the initial connection in a tool implementation.
"""

import asyncio
import logging
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from mcp.client.stdio import StdioServerParameters
from mcp.server.fastmcp import FastMCP, Context

from .smcp_sse_server import EnhancedSseServerSettings, run_enhanced_sse_server
from .session_utils import extract_session_param

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger(__name__)


# Create a FastMCP server
mcp = FastMCP("TechDebtCollector")


# Define a tool that uses session parameters
@mcp.tool()
async def collect_tech_debt(
    concept_name: str, 
    concept_description: str,
    code: str,
    file_path: str,
    start_line: int,
    end_line: int,
    references: Optional[List[str]] = None,
    project_context: Optional[Dict[str, Any]] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Collect a new tech debt entry
    
    Args:
        concept_name: Name of the tech debt concept
        concept_description: Description of what the concept is
        code: The code snippet that contains the tech debt
        file_path: Path to the file containing the tech debt
        start_line: Starting line number in the file
        end_line: Ending line number in the file
        references: Optional references to learn about this concept
        project_context: Optional additional project context
        ctx: Request context that may contain headers
    
    Returns:
        Dictionary with tech debt ID and status
    """
    # Handle default values for optional parameters
    if references == 0:
        references = None
    if project_context == 0:
        project_context = None
        
    # Ensure file_path is not empty
    if not file_path or file_path.strip() == "":
        file_path = "unknown_file.py"
        
    # Validate start and end lines
    if start_line <= 0:
        start_line = 1
    if end_line <= 0:
        end_line = start_line
    if end_line < start_line:
        end_line = start_line
    
    # Extract parameters from session data
    # Get auth parameter directly
    args = ctx.args if ctx else {}
    client_api_key = extract_session_param("auth", args, None)
    
    # We can also extract other session parameters
    client_id = extract_session_param("client_id", args, "unknown")
    
    logger.info(f"Processing tech debt request with API key: {client_api_key}")
    logger.info(f"Client ID from session: {client_id}")
        
    tech_debt_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    # Normally we would store the tech debt in a database
    # For this example, we just log it
    
    # Prepare data for forwarding
    forward_data = {
        "id": tech_debt_id,
        "concept_name": concept_name,
        "concept_description": concept_description,
        "code": code,
        "file_path": file_path,
        "start_line": start_line,
        "end_line": end_line,
        "references": references,
        "project_context": project_context,
        "timestamp": timestamp
    }
    
    # In a real implementation, we would forward to a backend with the API key
    if client_api_key:
        logger.info(f"Would forward to backend with API key: {client_api_key}")
        # backend_result = await forward_to_backend(forward_data, client_api_key)
        backend_result = {"status": "success", "message": "Data received by backend"}
    else:
        logger.warning("No API key found, storing locally only")
        backend_result = {"status": "error", "message": "No API key provided"}
    
    result = {
        "id": tech_debt_id,
        "status": "collected",
        "message": f"Tech debt '{concept_name}' has been collected and stored with ID {tech_debt_id}"
    }
    
    # Add backend forwarding result
    if backend_result:
        result["backend"] = backend_result
        
    return result


async def main():
    # Set up the SSE server with our enhanced implementation
    stdio_params = StdioServerParameters(
        command=["python", "-m", "mcp.client.stdio"]
    )
    
    sse_settings = EnhancedSseServerSettings(
        bind_host="localhost",
        port=8000,
        allow_origins=["*"],
        log_level="DEBUG",
    )
    
    # Run the enhanced SSE server
    await run_enhanced_sse_server(stdio_params, sse_settings)


if __name__ == "__main__":
    asyncio.run(main()) 