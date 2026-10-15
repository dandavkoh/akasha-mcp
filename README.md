
# 🔄 Akasha MCP

**A lightweight MCP-to-OpenAPI proxy for connecting AI agents with REST APIs and knowledge services.**

Akasha MCP exposes an API-oriented interface for integrating REST services with the Model Context Protocol (MCP). It is built with Python, FastAPI, Pydantic and Uvicorn and includes components for document processing, semantic search and vector indexing.

The project provides a foundation for connecting AI assistants and agent workflows to API-backed functionality.

## ✨ Features

- **MCP integration** — Connect MCP-compatible clients with available tools and services.
- **OpenAPI-oriented API layer** — Expose functionality through a REST interface.
- **FastAPI backend** — Build and serve HTTP endpoints using FastAPI.
- **Document processing** — Work with document ingestion and parsing components.
- **Semantic search** — Use embedding models and vector storage for retrieval workflows.
- **Vector indexing** — Integrate ChromaDB for indexing and similarity search.
- **OCR support** — Process scanned documents using OCR-related dependencies.
- **LDAP integration** — Includes dependencies for LDAP and Active Directory connectivity.
- **Container support** — Dockerfiles and Docker Compose configurations are included.

## 🧰 Technology Stack

| Technology | Purpose |
|---|---|
| Python 3.11+ | Runtime |
| FastAPI | HTTP API framework |
| Uvicorn | ASGI server |
| Pydantic | Data validation |
| MCP SDK | Model Context Protocol integration |
| LangChain | AI and retrieval integrations |
| Sentence Transformers | Text embeddings |
| ChromaDB | Vector storage and retrieval |
| Docling | Document parsing |
| OCR libraries | Text extraction from scanned documents |
| LDAP3 | LDAP and Active Directory integration |

## 📋 Requirements

- Python 3.11 or newer
- `uv` for Python package management
- Sufficient memory and disk space for the selected AI models
- Optional: Docker and Docker Compose for containerized execution
- Optional: access to an LDAP or Active Directory service if directory integration is required

Some machine-learning dependencies can be large. Installation time and resource requirements depend on your operating system and the models used.

## 🚀 Installation

### 1. Clone the repository

```bash
git clone https://github.com/dandavkoh/akasha-mcp.git
cd akasha-mcp
```

### 2. Install uv

If `uv` is not installed, follow the official instructions:

https://docs.astral.sh/uv/

Verify the installation:

```bash
uv --version
```

### 3. Install the project

Install the project and its dependencies into the active Python environment:

```bash
uv pip install --upgrade pip
uv pip install .
```

Make sure the active environment uses Python 3.11 or newer.

## ▶️ Quick Start

Start the API server from the repository root:

```bash
uvicorn mcp_openapi_proxy.proxy:app --host 0.0.0.0 --port 8000
```

The service will listen on port `8000`.

For local development, you can bind it to localhost instead:

```bash
uvicorn mcp_openapi_proxy.proxy:app --host 127.0.0.1 --port 8000
```

This avoids exposing the service to other machines on the network.

### Interactive API documentation

If the application exposes FastAPI's default documentation endpoints, open:

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

The available endpoints depend on the routes implemented and enabled in the current configuration.

## 🐳 Docker

The repository includes Dockerfiles and Docker Compose configurations for development and regular execution.

Inspect the available services and configuration before starting the containers:

```bash
docker compose config
```

Start the services defined in the default Compose file:

```bash
docker compose up --build
```

For development, use the dedicated configuration if required:

```bash
docker compose -f docker-compose.dev.yml up --build
```

Check the repository's Docker configuration for port mappings, environment variables, volumes and service dependencies.

## 🔌 MCP Integration

Akasha MCP is intended to connect AI clients with API-backed functionality through MCP.

A typical integration involves:

1. Starting the Akasha MCP service.
2. Configuring the target API or service.
3. Registering the MCP server with a compatible client.
4. Making the relevant tools available to the AI agent.
5. Testing requests and verifying access permissions.

**Important:** An HTTP endpoint is not automatically an MCP endpoint. Verify the implemented transport, available MCP tools and client configuration in the source code before connecting an agent.

## 🧠 Document Processing and Retrieval

The project includes dependencies for document parsing, OCR, embedding generation and vector storage.

These components can support workflows such as:

- Extracting text from documents.
- Processing scanned PDFs with OCR.
- Generating embeddings for text content.
- Indexing content in ChromaDB.
- Retrieving semantically relevant information.

The repository also defines an `index-chroma` command for its indexing functionality:

```bash
index-chroma --help
```

The exact input formats, index configuration and supported retrieval workflows depend on the implementation and configuration of the indexing modules.

## ⚙️ Configuration

Review the configuration files and documentation in the repository before running the service in a production environment.

Pay particular attention to:

- API URLs and network binding.
- Authentication and authorization.
- Environment variables and secrets.
- Document and index storage paths.
- Model downloads and resource consumption.
- LDAP configuration, if applicable.
- Docker volume and port settings.

Never commit API keys, passwords, access tokens or other secrets to version control.

## 📁 Project Structure

```text
akasha-mcp/
├── docu/                  # Project documentation
├── src/
│   ├── akasha_mcp/        # Akasha functionality and indexing
│   └── mcp_openapi_proxy/ # MCP/OpenAPI proxy implementation
├── Dockerfile             # Container build configuration
├── Dockerfile.dev         # Development container
├── docker-compose.yml     # Container orchestration
├── docker-compose.dev.yml # Development services
├── pyproject.toml         # Project metadata and dependencies
└── README.md              # Project documentation
```

## 🔐 Security

Before exposing the service beyond a trusted development environment:

- Bind to localhost unless remote access is required.
- Put authentication and authorization controls in place.
- Use HTTPS or a trusted reverse proxy for remote access.
- Restrict access to internal APIs and directory services.
- Validate incoming requests and uploaded documents.
- Avoid exposing sensitive documents through search results.
- Store credentials in environment-specific secret stores.
- Review Docker networking and volume permissions.

Binding to `0.0.0.0` makes the service listen on all available network interfaces. Do not use this setting on an untrusted network without appropriate access controls.

## 🛠️ Development

Install the project in your development environment:

```bash
uv pip install .
```

Run the API server:

```bash
uvicorn mcp_openapi_proxy.proxy:app --reload --host 127.0.0.1 --port 8000
```

If the development dependencies are required, install them according to the project's `pyproject.toml`.

Before submitting changes, verify that the application starts and that the relevant API and MCP workflows operate as expected.

## 🗺️ Roadmap

Potential areas for future development include:

- Expanded MCP client configuration examples.
- Clearer API authentication and authorization documentation.
- End-to-end tests for MCP and REST integrations.
- Document ingestion and indexing examples.
- Deployment guides for Docker and reverse proxies.
- Operational monitoring and structured logging.

These are possible improvement areas, not a statement that the features are already implemented.

## 🤝 Contributing

Contributions, bug reports and suggestions are welcome.

1. Fork the repository.
2. Create a feature branch.
3. Implement and test your changes.
4. Open a pull request with a clear description of the changes.

## 📄 License

Check the repository for a `LICENSE` file and the applicable terms before redistributing or using the project commercially.

## 🔗 Links

- **Repository:** https://github.com/dandavkoh/akasha-mcp
- **FastAPI:** https://fastapi.tiangolo.com/
- **uv:** https://docs.astral.sh/uv/
- **Model Context Protocol:** https://modelcontextprotocol.io/
- **ChromaDB:** https://docs.trychroma.com/

---

<p align="center">
  Built with Python, FastAPI and MCP.
</p>
