import debugpy
from mcp.server.fastmcp import FastMCP
from tools import math_tools, greeting_tools

mcp = FastMCP("python-mcp")

math_tools.register(mcp)
greeting_tools.register(mcp)

if __name__ == "__main__":
    debugpy.listen(("0.0.0.0", 5678))
    print("🧲 Debugger listening on port 5678")
    #debugpy.wait_for_client()

    mcp.run()