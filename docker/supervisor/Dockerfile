# Dockerfile for Supervisor Service (Port 7703)

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY astra-os/services/supervisor/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY astra-os/services/supervisor/ .

# Expose port
EXPOSE 7703

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:7703/health || exit 1

# Run as non-root user
RUN useradd -m -u 1000 supervisor && chown -R supervisor:supervisor /app
USER supervisor

# Start service
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7703"]
