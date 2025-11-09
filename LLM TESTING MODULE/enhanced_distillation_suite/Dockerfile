FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04
RUN apt-get update && apt-get install -y git python3.11 python3.11-venv && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace
COPY requirements.txt /workspace/requirements.txt
RUN python3.11 -m venv /opt/venv && /opt/venv/bin/pip install -U pip && /opt/venv/bin/pip install -r /workspace/requirements.txt
ENV PATH="/opt/venv/bin:$PATH"
COPY . /workspace
CMD ["/bin/bash"]