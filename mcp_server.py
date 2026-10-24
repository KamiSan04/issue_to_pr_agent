from mcp.server.fastmcp import FastMCP

import tools

mcp = FastMCP("issue-to-pr-tools")

for function in tools.TOOL_FUNCTIONS:
    mcp.tool()(function)

if __name__ == "__main__":
    mcp.run(transport="stdio")