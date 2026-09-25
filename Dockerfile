FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv and add to PATH
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# The release this image was built from (deploy.yml passes the release tag).
ARG APP_VERSION=dev
ENV APP_VERSION=$APP_VERSION

# Copy project files
COPY pyproject.toml uv.lock ./
COPY . .

# Install dependencies
RUN uv sync --frozen

# Create non-root user
#RUN useradd -m -u 1000 scanova && chown -R scanova:scanova /app
#USER scanova

# Expose port (if using HTTP transport)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run the HTTP server instead of stdio server
CMD ["uv", "run", "src/cloud_server.py"]