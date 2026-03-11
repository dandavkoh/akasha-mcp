import os, sys
import json
from typing import Dict, Any
from urllib import request
import mcp.types as types

from fastapi import FastAPI, Body, Request
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
# Helper function to parse MCP tool results robustly
# -----------------------------
def parse_mcp_result(raw: Any) -> Any:
    """
    Safely extract the "real" value from MCP tool output.

    Handles:
      - tuple: (TextContent list, {'result': ...})
      - dict with 'result'
      - single TextContent
      - plain value (str, int, etc.)
      - JSON-encoded strings
    """
    
    # Step 1: Unwrap tuple (common MCP client return)
    if isinstance(raw, tuple) and len(raw) == 2:
        raw = raw[1]  # take the structured Python return value
    
    # Step 2: If dict with 'result', extract it
    if isinstance(raw, dict) and 'result' in raw:
        value = raw['result']
    else:
        value = raw

    # Step 3: If value is a list of TextContent, join text
    if isinstance(value, list) and all(hasattr(v, 'text') for v in value):
        text = "".join(v.text for v in value)
        value = text

    # Step 4: If value is a TextContent object itself
    if hasattr(value, 'text'):
        value = value.text

    # Step 5: Attempt JSON decode if looks like JSON
    if isinstance(value, str):
        value = value.strip()
        if (value.startswith('{') and value.endswith('}')) or \
           (value.startswith('[') and value.endswith(']')):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass  # keep as string if invalid JSON

    return value

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
            async def tool_endpoint(form_data: FormModel, request: Request):
                args = form_data.model_dump()

                authorization = request.headers.get("authorization")
                user_id = request.headers.get("x-openwebui-user-id")
                user_email = request.headers.get("x-openwebui-user-email")
                user_name = request.headers.get("x-openwebui-user-name")
                user_role = request.headers.get("x-openwebui-user-role")
                chat_id = request.headers.get("x-openwebui-chat-id")
                message_id = request.headers.get("x-openwebui-message-id")

                args["user_context"] = {
                    "authorization": authorization[7:] if authorization and authorization.startswith("Bearer ") else "",
                    "user_id": user_id or "",
                    "user_email": user_email or "",
                    "user_name": user_name or "",
                    "user_role": user_role or "",
                    "chat_id": chat_id or "",
                    "message_id": message_id or ""
                }

                result = await mcp.call_tool(endpoint_name, args)

                response = []
                response.append(parse_mcp_result(result))

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
# Optional Embedded Start
# -----------------------------
if __name__ == "__main__":
    args = parse_args()

    import uvicorn
    uvicorn.run("mcp_openapi_proxy.main:app", host=args.host, port=args.port, reload=True)