FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# Environment variables
ENV PYTHONPATH=/app
ENV ASTRA_CONFIG=/app/config/rag.yaml
ENV ASTRA_DATA=/data

# Create necessary directories
RUN mkdir -p /data/ingest/inbox \
    /data/ingest/processed \
    /data/ingest/failed \
    /data/logs \
    /data/telemetry \
    /data/cache

# Run the service
CMD ["python", "-m", "src.astra.service.ingestion_service"]