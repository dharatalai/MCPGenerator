# Generated MCP Server
from mcp.server.fastmcp import FastMCP

mcp = FastMCP('generated_mcp')

@mcp.tool()
async def example_tool(query: str):
    """Example tool"""
    return {'result': f'Processed: {query}'}

if __name__ == "__main__":
    mcp.run()