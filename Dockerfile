# GitLab Backport Bot Service Dockerfile
# Multi-stage build for optimized production image

# ========== Stage 1: Builder ==========
FROM python:3.11-slim as builder

# Set build arguments
ARG POETRY_VERSION=1.7.1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /build

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ========== Stage 2: Production ==========
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_HOME=/app \
    PORT=8080 \
    HOST=0.0.0.0 \
    LOG_LEVEL=INFO

# Set working directory
WORKDIR $APP_HOME

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY app/ ./app/
COPY scripts/ ./scripts/

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser \
    && chown -R appuser:appuser $APP_HOME

# Switch to non-root user
USER appuser

# Expose port
EXPOSE $PORT

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:$PORT/health/ || exit 1

# Run the application
CMD ["python", "-m", "app.main"]

# Metadata
LABEL maintainer="GitLab Bot User <bot@example.com>" \
      description="GitLab Backport Bot Service" \
      version="1.0.0"
