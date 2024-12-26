import logging
import typing as t

from mcp import server, types
from mcp.client.session import ClientSession

logger = logging.getLogger(__name__)


async def confugure_app(name: str, remote_app: ClientSession):
    app = server.Server(name)

    async def _list_prompts(_: t.Any) -> types.ServerResult:
        result = await remote_app.list_prompts()
        return types.ServerResult(result)

    app.request_handlers[types.ListPromptsRequest] = _list_prompts

    async def _get_prompt(req: types.GetPromptRequest) -> types.ServerResult:
        result = await remote_app.get_prompt(req.params.name, req.params.arguments)
        return types.ServerResult(result)

    app.request_handlers[types.GetPromptRequest] = _get_prompt

    async def _list_resources(_: t.Any) -> types.ServerResult:
        result = await remote_app.list_resources()
        return types.ServerResult(result)

    app.request_handlers[types.ListResourcesRequest] = _list_resources

    # list_resource_templates() is not implemented in the client
    # async def _list_resource_templates(_: t.Any) -> types.ServerResult:
    #     result = await remote_app.list_resource_templates()
    #     return types.ServerResult(result)

    # app.request_handlers[types.ListResourceTemplatesRequest] = _list_resource_templates

    async def _read_resource(req: types.ReadResourceRequest):
        result = await remote_app.read_resource(req.params.uri)
        return types.ServerResult(result)

    app.request_handlers[types.ReadResourceRequest] = _read_resource

    async def _set_logging_level(req: types.SetLevelRequest):
        await remote_app.set_logging_level(req.params.level)
        return types.ServerResult(types.EmptyResult())

    app.request_handlers[types.SetLevelRequest] = _set_logging_level

    async def _subscribe_resource(req: types.SubscribeRequest):
        await remote_app.subscribe_resource(req.params.uri)
        return types.ServerResult(types.EmptyResult())

    app.request_handlers[types.SubscribeRequest] = _subscribe_resource

    async def _unsubscribe_resource(req: types.UnsubscribeRequest):
        await remote_app.unsubscribe_resource(req.params.uri)
        return types.ServerResult(types.EmptyResult())

    app.request_handlers[types.UnsubscribeRequest] = _unsubscribe_resource

    async def _list_tools(_: t.Any):
        tools = await remote_app.list_tools()
        return types.ServerResult(tools)

    app.request_handlers[types.ListToolsRequest] = _list_tools

    async def _call_tool(req: types.CallToolRequest) -> types.ServerResult:
        try:
            result = await remote_app.call_tool(
                req.params.name, (req.params.arguments or {})
            )
            return types.ServerResult(result)
        except Exception as e:
            return types.ServerResult(
                types.CallToolResult(
                    content=[types.TextContent(type="text", text=str(e))],
                    isError=True,
                )
            )

    app.request_handlers[types.CallToolRequest] = _call_tool

    async def _send_progress_notification(req: types.ProgressNotification):
        await remote_app.send_progress_notification(
            req.params.progressToken, req.params.progress, req.params.total
        )

    app.notification_handlers[types.ProgressNotification] = _send_progress_notification

    async def _complete(req: types.CompleteRequest):
        result = await remote_app.complete(
            req.params.ref, req.params.argument.model_dump()
        )
        return types.ServerResult(result)

    app.request_handlers[types.CompleteRequest] = _complete

    async with server.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


async def run_sse_client(url: str):
    from mcp.client.sse import sse_client

    async with sse_client(url=url) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            response = await session.initialize()

            await confugure_app(response.serverInfo.name, session)
