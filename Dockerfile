# Use Python 3.12 slim image
FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy project files
WORKDIR /app
COPY pyproject.toml .
COPY README.md .
COPY src/ src/

# Install dependencies and package
RUN uv sync --no-dev --frozen

# Default command: run MCP server via stdio
CMD ["uv", "run", "mcp-eastmoney"]
