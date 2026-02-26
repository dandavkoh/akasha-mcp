import os, sys
import json
from typing import Dict, Any

from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import create_model

# Embedded MCP import
from akasha_mcp.server import mcp

# DEV_MODE debugger only in development worker (not the reloader parent)
if os.environ.get("DEV_MODE") == "true" and os.environ.get("PYCHARM_HOSTED", "0") != "1":
    # uvicorn's reload spawns a reloader process; try to only attach in the child worker:
    if os.environ.get("UVICORN_RELOAD") == "true" or "uvicorn" in " ".join(sys.argv):
        import debugpy
        try:
            debugpy.listen(("0.0.0.0", 5678))
            print("🧲 Debugger listening on port 5678")
            #debugpy.wait_for_client()
        except Exception:
            pass

# -----------------------------
# FastAPI App global for uvicorn --reload
# -----------------------------
app = FastAPI(
    title=getattr(mcp, "name", "Embedded MCP"),
    description="Embedded MCP + FastAPI Proxy",
    version="1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# Dynamic Endpoint Generation
# -----------------------------
async def create_dynamic_endpoints(app: FastAPI):
    """
    Dynamically creates FastAPI endpoints based on registered MCP tools.
    """

    # 1. Retrieve tools
    try:
        tools_result = await mcp.list_tools()
        if isinstance(tools_result, list):
            tools = tools_result
        else:
            tools = getattr(tools_result, "tools", [])
    except Exception:
        # fallback: iterate over mcp.tool.keys() if available
        try:
            tools = [t for t in getattr(mcp, "tool", {}).values()]
        except Exception:
            tools = []

    # 2. Create endpoints
    for tool in tools:
        endpoint_name = tool.name
        endpoint_description = getattr(tool, "description", "")
        schema = getattr(tool, "inputSchema", {"properties": {}, "required": []})

        model_fields = {}
        required_fields = schema.get("required", [])

        for param_name, param_schema in schema.get("properties", {}).items():
            param_type = param_schema.get("type", "string")
            param_desc = param_schema.get("description", "")

            python_type = str
            if param_type == "string":
                python_type = str
            elif param_type == "integer":
                python_type = int
            elif param_type == "boolean":
                python_type = bool
            elif param_type == "number":
                python_type = float
            elif param_type == "object":
                python_type = Dict[str, Any]
            elif param_type == "array":
                python_type = list

            default_value = ... if param_name in required_fields else None

            model_fields[param_name] = (
                python_type,
                Body(default_value, description=param_desc),
            )

        FormModel = create_model(f"{endpoint_name}_form_model", **model_fields)

        # Create endpoint function
        def make_endpoint_func(endpoint_name: str, FormModel):
            async def tool_endpoint(form_data: FormModel):
                args = form_data.model_dump()
                result = await mcp.call_tool(endpoint_name, args)

                # robust against Tuple or ToolCallResult
                if isinstance(result, tuple):
                    content_list = result[0]  # first element is the actual content list
                else:
                    content_list = getattr(result, "content", [])

                response = []
                for content in content_list:
                    text = getattr(content, "text", content)  # if content is directly a string
                    if isinstance(text, str):
                        try:
                            text = json.loads(text)
                        except json.JSONDecodeError:
                            pass
                    response.append(text)

                return response

            return tool_endpoint

        endpoint_func = make_endpoint_func(endpoint_name, FormModel)

        app.post(
            f"/{endpoint_name}",
            summary=endpoint_name.replace("_", " ").title(),
            description=endpoint_description,
        )(endpoint_func)


# -----------------------------
# FastAPI Startup Event
# -----------------------------
@app.on_event("startup")
async def on_startup():
    await create_dynamic_endpoints(app)


# -----------------------------
# CLI Args (optional)
# -----------------------------
def parse_args():
    import argparse
    parser = argparse.ArgumentParser(description="Embedded FastAPI MCP OpenAPI Proxy")
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    return parser.parse_args()


# -----------------------------
# Optionaler Embedded Start
# -----------------------------
if __name__ == "__main__":
    args = parse_args()

    import uvicorn
    uvicorn.run("mcp_openapi_proxy.main:app", host=args.host, port=args.port, reload=True)