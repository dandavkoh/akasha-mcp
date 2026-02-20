from mcp.server.fastmcp import FastMCP
from tools import math_tools, greeting_tools

mcp = FastMCP("python-mcp")

math_tools.register(mcp)
greeting_tools.register(mcp)

if __name__ == "__main__":
    mcp.run()