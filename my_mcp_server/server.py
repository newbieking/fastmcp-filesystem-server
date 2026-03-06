# src/my_mcp_server/filesystem_server.py
import asyncio

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool, Resource

# 初始化 MCP Server
app = Server("my-mcp-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """声明可用工具"""
    return [
        Tool(
            name="calculate_sum",
            description="计算两个数字之和",
            inputSchema={
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"}
                },
                "required": ["a", "b"]
            }
        ),
        Tool(
            name="get_weather",
            description="获取城市天气",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {"type": "string"}
                },
                "required": ["city"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """执行工具调用"""
    if name == "calculate_sum":
        result = arguments["a"] + arguments["b"]
        return [TextContent(type="text", text=str(result))]

    elif name == "get_weather":
        city = arguments["city"]
        # 实际应调用天气 API
        # service = OpenWeatherService(os.getenv("OPENWEATHER_API_KEY"))
        # result = await service.get_current(arguments["city"])
        # return [TextContent(type="text", text=str(result))]
        return [TextContent(type="text", text=f"{city} 天气：晴天 25°C")]

    raise ValueError(f"未知工具: {name}")


@app.list_resources()
async def list_resources() -> list[Resource]:
    """声明可用资源"""
    return [
        Resource(
            uri="file:///config/app.json",
            name="应用配置",
            mimeType="application/json"
        )
    ]


@app.read_resource()
async def read_resource(uri: str) -> str:
    """读取资源内容"""
    if uri == "file:///config/app.json":
        return '{"version": "1.0.0", "debug": true}'
    raise ValueError(f"未知资源: {uri}")


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())