FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libsndfile1 curl \
  && rm -rf /var/lib/apt/lists/*

COPY services/documents/requirements.docs.txt ./requirements.docs.txt
RUN pip install --no-cache-dir -r requirements.docs.txt

COPY services/documents /app

# create index/data dirs
RUN mkdir -p /data/index /data/documents /data/models \
    && useradd -m -u 1001 astra
USER 1001

EXPOSE 8777
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8777", "--workers", "1"]# services/documents/Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System deps for pymupdf
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libjpeg62-turbo-dev zlib1g-dev libopenjp2-7-dev libfreetype6-dev \
    libxcb1 libxcb-render0 libxcb-shm0 poppler-utils && \
    rm -rf /var/lib/apt/lists/*

COPY services/documents/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src /app/src

RUN mkdir -p /data/index /data/documents && chown -R 1000:1000 /data
USER 1000

ENV DOC_INDEX_DIR=/data/index
EXPOSE 8000

CMD ["python", "-m", "astra.services.document_service", "--help"]
