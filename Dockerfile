# =============================================================================
# MULTI-STAGE DOCKER BUILD - OPTIMIZED FOR PRODUCTION
# =============================================================================
# Build Stage: Install dependencies and compile packages
# Runtime Stage: Minimal runtime environment with only necessary files
# Expected reduction: 40-60% smaller final image
# =============================================================================

# -----------------------------------------------------------------------------
# BUILD STAGE - Install dependencies and compile packages
# -----------------------------------------------------------------------------
FROM python:3.11-slim as builder

# Install build dependencies (only needed during build)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    pkg-config \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment for cleaner dependency management
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    pip check

# -----------------------------------------------------------------------------
# RUNTIME STAGE - Minimal production environment  
# -----------------------------------------------------------------------------
FROM python:3.11-slim as runtime

# Install runtime system dependencies (minimal set including health check tools)
RUN apt-get update && apt-get install -y \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app

# Copy only application files (no build artifacts, git, etc.)
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser static/ ./static/
COPY --chown=appuser:appuser templates/ ./templates/

# Switch to non-root user
USER appuser

# Add health check for container orchestration
# Use liveness endpoint for quick container health validation
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/health/live || exit 1

# Expose application port
EXPOSE 8080

# Production-optimized startup command
CMD ["python", "-m", "uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8080", \
     "--workers", "1", \
     "--access-log"]