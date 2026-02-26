from mcp.server.fastmcp import FastMCP
from akasha_mcp.tools import math_tools, greeting_tools, nas_tools

mcp = FastMCP("python-mcp")

math_tools.register(mcp)
greeting_tools.register(mcp)
nas_tools.register(mcp)

if __name__ == "__main__":
    mcp.run()