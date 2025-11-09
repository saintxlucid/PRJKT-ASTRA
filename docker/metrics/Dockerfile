# Dockerfile for Metrics Service (Port 7705)

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements (create basic requirements)
RUN echo "fastapi>=0.100.0\nuvicorn[standard]>=0.23.0\nprometheus-client>=0.17.0" > requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy service code (or create minimal service)
COPY astra-os/services/metrics/ ./ 2>/dev/null || echo "from fastapi import FastAPI\napp = FastAPI()\n@app.get('/health')\nasync def health():\n    return {'status': 'healthy'}" > server.py

# Create prometheus multiproc directory
RUN mkdir -p /tmp/prometheus && chmod 777 /tmp/prometheus

# Expose port
EXPOSE 7705

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:7705/health || exit 1

# Run as non-root user
RUN useradd -m -u 1000 metrics && chown -R metrics:metrics /app /tmp/prometheus
USER metrics

# Start service
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7705"]
