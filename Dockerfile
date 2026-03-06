FROM python:3.12-slim-bookworm

# Install uv (from official binary) and git
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Docling dependencies (for NAS indexing)
# RUN apt-get update && apt-get install -y \
#     libxcb1 \
#     libx11-6 \
#     libxext6 \
#     libsm6 \
#     libice6 \
#     libgl1 \
#  && rm -rf /var/lib/apt/lists/*

# Copy the source code (assuming in src/) and change to the app directory
COPY . /app
WORKDIR /app

# Create virtual environment explicitly in known location
ENV VIRTUAL_ENV=/app/.venv
RUN uv venv "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install mcp (assuming pyproject.toml is properly configured)
COPY pyproject.toml pyproject.toml
COPY README.md README.md
RUN uv pip install --upgrade pip
RUN uv pip install .

# Expose port (optional but common default)
EXPOSE 8000

# Run the server
CMD ["sh", "-c", "uvicorn mcp_openapi_proxy.proxy:app --host 0.0.0.0 --port 8000"]