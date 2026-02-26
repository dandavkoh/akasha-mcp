# 🔄 MCP Server with OpenAPI Proxy

This folder implements an MCP tool servers proxied through an OpenAPI-compatible REST APIs interface.

## 🔧 Quick Start

Make sure uv is installed and available.

Install dependencies:

```bash
uv pip install --upgrade pip
uv pip install .
```

Run the server:

```bash
uvicorn mcp_openapi_proxy.proxy:app --host 0.0.0.0 --port 8000
```

THE MCP server will now be available as an OpenAPI-compatible API.