# session.mcp

This is a straightforward SSE session-based easy remote SSE authorization, per-user information processing solution based on little modification on MCP's python-sdk, I added a few things in SSE's implementation `sse.py` + `FastMCP` component.  

The main reason I created this is how MCP's authorization problem is a pain in the butt. First of all if you're not aware of it, MCP doesn't have an authorization service. It's the first thing in their roadmap but it will still take them a while to start work on it. 

My past ideal solution was to create a worker/forwarding service, that for example, creates a worker page on `mcp-auth.example.io/<k/API-KEY>`, then forwards requests to `mcp.example.io` with `<API-KEY>`. But as you know it didn't work out (or I wouldn't be creating this mcp plugin) since MCP processes `SSE` URLs in a weird way that you can't input `mcp-auth.example.io/<k/API-KEY>/sse/` and expect the client to expect the `message` endpoint at `mcp-auth.example.io/<k/API-KEY>/message/`. (the client will expect the message endpoint at `mcp-auth.example.io/message` so nothing much we can do).

A simple solution on MCP authorization mattered for me since I am creating a MCP based SaaS startup that focused on techdebts (the thing is not about collecting TechDebts but how you process, build it and pay-off them for the users), and it can't work without easy authorization. And you can't really expect everyone else to deploy a local MCP server, *we're lazy and we want easy access.*  So I read a little about MCP's source, turned out they have an implementation for `session_id` but just for client stream storing. So I added a little thing for the `session_id` to 

## Installation

You can install the package using the provided install script:

```bash
# Clone the repository
git clone https://github.com/sparfenyuk/session.mcp.git
cd session.mcp

# Run the install script
chmod +x install.sh
./install.sh
```

Or install it manually:

```bash
# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package
pip install -e .
```

## CLI Commands

SessionMCP provides several CLI commands:

- `sessionmcp` - The standard SessionMCP proxy
- `smcp` - Shorthand alias for sessionmcp
- `sessionmcp-enhanced` - Always use the enhanced SSE server with session parameter support

### Example Usage

```bash
# Start a standard MCP proxy server on port 8080
sessionmcp --sse-port 8080 -- python -m mcp.client.stdio

# Start an enhanced MCP proxy with session parameter support
sessionmcp --sse-port 8080 --enhanced -- python -m mcp.client.stdio

# Or use the dedicated enhanced command
sessionmcp-enhanced --sse-port 8080 -- python -m mcp.client.stdio 

# Use with FastMCP
sessionmcp-enhanced --sse-port 8080 -- python my_fastmcp_script.py
```

## What is this for:
Cursor and lots of LLM IDEs support MCP, there are two ways of running an MCP, `stdio` / `sse`. 
For `stdio` you run the MCP server locally, for `SSE` you're able to connect to a MCP server. `mcp-proxy` allows you to host a MCP server, but authorization for MCP servers is always a pain in the butt. MCP local dev allows you to set up authorization headers but other clients do not. `session.mcp` provides an easy solution by enhancing the MCP original `session_id` implementation to store information. For example, you can input this URL in Cursor.

```
http://example.io/sse?auth=<APIKEY>&service=<service_type>
```

And pass these info to the backend.

## How does `session_id` in SSE work?

Here's the usual SSE communication:
```
INFO:     172.71.182.62:11448 - "GET /sse HTTP/1.1" 200 OK
DEBUG:mcp.server.sse:Starting SSE writer
DEBUG:mcp.server.sse:Sent endpoint event: /messages/?session_id=x
DEBUG:sse_starlette.sse:chunk: b'event: endpoint\r\ndata: /messages/?session_id=x\r\n\r\n'
DEBUG:mcp.server.sse:Handling POST message
DEBUG:mcp.server.sse:Parsed session ID: x
DEBUG:mcp.server.sse:Received JSON: {'jsonrpc': '2.0', 'id': 0, 'method': 'initialize', 'params': {....}, jsonrpc='2.0', id=0)

INFO:     141.101.76.4:42640 - "POST /messages/?session_id=x HTTP/1.1" 202 Accepted
DEBUG:mcp.server.sse:Sending message via SSE: root=JSONRPCResponse({...})
DEBUG:sse_starlette.sse:chunk: b'event: message\r\ndata: {///}\r\n\r\n'
DEBUG:mcp.server.sse:Handling POST message
DEBUG:mcp.server.sse:Parsed session ID: x
DEBUG:mcp.server.sse:Received JSON: {...}
DEBUG:mcp.server.sse:Validated client message: root=JSONRPCNotification(...)
DEBUG:mcp.server.sse:Sending message to writer: root=JSONRPCNotification(..)
```
1. `/sse` -> `initialize` an MCP connection, notice that it returns you with `/messages/?` with returned `session_id`, then the initialization is done @ `/messages/?` with your obtained session ID in `/sse`, so `/sse` is more like a constructor
2. `/message` -> deals with all the MCP tools call, resources, prompts, ping, roots. e.g. this is what happens when you call for a tool.

```
[03/13/25 01:13:37] INFO     Processing request of type CallToolRequest                                                                                               server.py:534
DEBUG:mcp.server.lowlevel.server:Response sent
DEBUG:mcp.server.sse:Sending message via SSE: root=JSONRPCResponse(jsonrpc='2.0', id=4, result={'content': [], 'isError': false})
DEBUG:sse_starlette.sse:chunk: b'event: message\r\ndata: {"jsonrpc":"2.0","id":4,"result":{"content":[],"isError":false}}\r\n\r\n'
```

## Session Parameters

The enhanced SSE server in SessionMCP extends the standard SSE server to capture and store query parameters from the initial connection URL:

```
http://localhost:8080/sse?auth=YOUR_API_KEY&client_id=YOUR_CLIENT_ID
```

These parameters are associated with the session ID and can be accessed in tool implementations:

```python
@mcp.tool()
async def your_tool(param1: str, ctx: Context = None) -> Dict[str, Any]:
    args = ctx.args if ctx else {}
    
    # Extract parameters from the initial connection URL
    auth_token = extract_session_param("auth", args, None)
    client_id = extract_session_param("client_id", args, "unknown")
    
    # Use the parameters in your implementation
    if auth_token:
        # Make authenticated request
        result = await call_authenticated_service(param1, auth_token)
    else:
        # Fall back to public access
        result = await call_public_service(param1)

    return result
```

## Session?
The `session_id` in MCP is originally used to link these two communication channels:

1. When a client connects via `connect_sse()`, a new `UUID` is generated:
	* `session_id = uuid4()` (`src/mcp/server/sse.py:97`)
2. Sends the session URI to the client via the first SSE event:
	```python
	session_uri = f"{quote(self._endpoint)}?session_id={session_id.hex}"
    self._read_stream_writers[session_id] = read_stream_writer
	```
3. Maintains a dictionary mapping session IDs to stream writers:
    ```python
    self._read_stream_writers[session_id] = read_stream_writer
    ```
* When a client sends a POST request, it must include the session ID:
    ```python
    session_id_param = request.query_params.get("session_id")
    ```
* Validates the `session_id` and retrieves the associated stream:
    ```python
    session_id = UUID(hex=session_id_param)
    writer = self._read_stream_writers.get(session_id)
    ```


## How It Works

1. **Connection Phase**: When a client connects to the `/sse` endpoint, it can include query parameters:
   ```
   example.io/sse?auth=API_KEY&user_id=12345 HTTP/1.1
   ```

2. **Session Storage**: These parameters are captured and associated with the generated session ID:
   ```python
   # SseServerTransport automatically captures and stores these parameters
   session_params = {
     'auth': 'API_KEY',
     'user_id': '12345'
   }
   ```

3. **Access in Tools and Resources**: Access the session data through the Context object:
   ```python
   @server.tool()
   def authenticated_tool(data: str, ctx: Context) -> str:
       # Get authentication key from session data
       auth_key = extract_session_param("auth", ctx.args, None)
       
       if not auth_key or not is_valid_key(auth_key):
           return "Unauthorized access"
           
       return process_data(data)
   ```

## Client Connection

Clients should connect to the SSE endpoint with the necessary parameters:

```javascript
const eventSource = new EventSource('/sse?auth=API_KEY&user_id=12345');

eventSource.addEventListener('endpoint', (event) => {
    const messagesEndpoint = event.data;
});
```