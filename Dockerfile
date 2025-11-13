FROM ghcr.io/astral-sh/uv:python3.12-trixie-slim

WORKDIR /app

# Install system dependencies (if needed for any packages)
RUN apt-get update && apt-get install -y

# Copy application code
COPY . /app
COPY uv.lock pyproject.toml /app/

# Install dependencies
RUN uv sync --locked

# Create necessary directories
RUN mkdir -p data logs certs

# Expose ports
EXPOSE 8080 8443

# Default command (can be overridden)
CMD ["uvicorn", "personal_health.core:app", "--host", "0.0.0.0", "--port", "8080"]
