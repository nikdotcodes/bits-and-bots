# Build stage
FROM python:3.14-slim AS builder

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy project files needed for building
COPY pyproject.toml uv.lock README.md ./
COPY src ./src

# Install dependencies
RUN uv sync --frozen

# Runtime stage
FROM python:3.14-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY src ./src
COPY .env ./.env

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/', timeout=5)" || exit 1

# Run the application
CMD ["uvicorn", "bits_and_bots.main:app", "--host", "0.0.0.0", "--port", "8000"]
