# ==============================================================================
# OpenLocalRagAgents — Enterprise Production Dockerfile
# Multi-stage optimized build for Python 3.11 with CUDA / CPU PyTorch
# ==============================================================================

FROM python:3.11-slim

# Environment settings
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    TOKENIZERS_PARALLELISM=false

WORKDIR /app

# Install minimal OS build tools and curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch with CUDA 12.1 support (falls back to CPU if no GPU available)
RUN pip install --no-cache-dir torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu121

# Install project dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary persistent volume mount directories
RUN mkdir -p /app/data /app/models /app/vector_db

# Copy project source code
COPY . /app

# Expose backend API (8000) and frontend Streamlit (8501) ports
EXPOSE 8000 8501

# Healthcheck monitoring the FastAPI backend
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/stats || exit 1

# Default command launches the FastAPI gateway
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
