"""A tiny MCP server (stdio) with one noisy tool, standing in for any real MCP server."""

from demo_logs import search_logs

try:
    from mcp.server.fastmcp import FastMCP as Server
except ImportError:
    from mcp.server.mcpserver import MCPServer as Server

server = Server("logs")
server.tool()(search_logs)

if __name__ == "__main__":
    server.run("stdio")
