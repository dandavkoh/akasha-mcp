FROM python:3.12-slim-bookworm

# Install uv (from official binary), nodejs, npm, and git
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js and npm via NodeSource
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Confirm npm and node versions (optional debugging info)
RUN node -v && npm -v

# Copy your mcpo source code (assuming in src/) and change to the app directory
COPY . /app
WORKDIR /app

# Create virtual environment explicitly in known location
ENV VIRTUAL_ENV=/app/.venv
RUN uv venv "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install mcpo and mcp(assuming pyproject.toml is properly configured)
RUN uv pip install . && rm -rf ~/.cache

# Verify mcpo and mcp installed correctly
RUN which mcpo
RUN which mcp

# Expose port (optional but common default)
EXPOSE 8000

# Run the server
CMD ["sh", "-c", "mcpo --api-key \"$MCPO_API_KEY\" -- python /app/src/mcp/server.py"]