FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (if needed for any packages)
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . /app

# Install uv for dependency management
RUN pip install uv

# Install dependencies
RUN uv sync

# Create necessary directories
RUN mkdir -p data models logs certs

# Expose ports
EXPOSE 8080 8443

# Default command (can be overridden)
CMD ["uvicorn", "personal_health.core:app", "--host", "0.0.0.0", "--port", "8080"]
