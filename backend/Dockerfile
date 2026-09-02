# Multi-stage build: production-ready Flask backend
# Optimized for AWS ECS, Lambda, or EC2 deployment

# Stage 1: Builder
FROM python:3.9-slim as builder

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.9-slim

WORKDIR /app

# Install runtime dependencies only (security: reduce attack surface)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies into the interpreter's system path so the
# non-root runtime user can import them.
COPY --from=builder /install /usr/local

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_ENV=production

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 cloudguard && chown -R cloudguard:cloudguard /app
USER cloudguard

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5001/api/stats || exit 1

# Expose port (can be overridden with -e PORT=xxxx)
EXPOSE 5001

# Start Flask app
CMD ["python", "app.py"]
