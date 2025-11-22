from mcp.client import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import json


class PortfolioMCPClient:
    def __init__(self):
        self.session = None

    async def connect(self):
        """Connect to MCP server"""
        server_params = StdioServerParameters(
            command="python",
            args=["mcp_server.py"]
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                self.session = session
                await session.initialize()

    async def call_tool(self, tool_name, **kwargs):
        """Call MCP tool"""
        result = await self.session.call_tool(tool_name, arguments=kwargs)
        return json.loads(result.content[0].text)


# Singleton
_client = None


def get_mcp_client():
    global _client
    if _client is None:
        _client = PortfolioMCPClient()
    return _client