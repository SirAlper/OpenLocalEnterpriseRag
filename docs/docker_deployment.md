# 🐳 Docker Deployment Guide

This guide details how to deploy `OpenLocalEnterpriseRag` using **Docker** and **Docker Compose** for production and on-premise enterprise environments.

---

## 🏗️ Architecture Overview

The containerized deployment splits the platform into two decoupled services communicating over an internal Docker bridge network:

```text
┌─────────────────────────────────────────────────────────────┐
│                       Host Machine                          │
│                                                             │
│   ┌──────────────────┐               ┌──────────────────┐   │
│   │  ./models/       │               │  ./vector_db/    │   │
│   │  (Weights ~6GB)  │               │  (ChromaDB)      │   │
│   └────────┬─────────┘               └────────┬─────────┘   │
│            │ (Volume)                         │ (Volume)    │
│            ▼                                  ▼             │
│   ┌─────────────────────────────────────────────────────┐   │
│   │           enterprise_rag_backend (Port 8000)        │   │
│   │       FastAPI + LangGraph + PyTorch (GPU/CPU)       │   │
│   └──────────────────────────▲──────────────────────────┘   │
│                              │ (Internal Network: http)     │
│   ┌──────────────────────────┴──────────────────────────┐   │
│   │          enterprise_rag_frontend (Port 8501)        │   │
│   │           Streamlit Web Management UI               │   │
│   └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

* **Zero-Bloat Image:** Model weights (`models/`), vector indexes (`vector_db/`), and enterprise documents (`data/`) are mounted dynamically as external volumes. The Docker image remains compact (~1.5 GB).
* **Data Persistence:** Rebuilding or updating containers never deletes your documents or vectorized data.

---

## 📋 Prerequisites

| Requirement | CPU Mode | NVIDIA GPU Mode |
| :--- | :--- | :--- |
| **Docker Engine** | Version 24.0+ | Version 24.0+ |
| **Docker Compose** | Compose v2 (`docker compose`) | Compose v2 (`docker compose`) |
| **NVIDIA Driver** | Not required | Version 525+ |
| **Container Toolkit** | Not required | [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) |

---

## ⚡ Quickstart in 3 Steps

### Step 1: Provision Local Models
Before starting the containers, download the required local models to `./models`:
```bash
python download_model.py
```
*(If you do not have Python installed on the host, you can also download them inside a temporary container or copy existing weights into `./models`).*

### Step 2: Launch the Services

#### Option A: CPU Execution (Default)
```bash
docker compose up -d --build
```

#### Option B: NVIDIA GPU Acceleration (CUDA)
To pass host NVIDIA GPUs directly to the backend container:
```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```

### Step 3: Access Applications
* **Streamlit Web UI:** `http://localhost:8501`
* **FastAPI Swagger API:** `http://localhost:8000/docs`
* **Healthcheck API:** `http://localhost:8000/api/v1/stats`

---

## 🔍 Useful Operational Commands

### View Logs in Real-time:
```bash
# All services
docker compose logs -f

# Backend API only
docker compose logs -f backend

# Frontend UI only
docker compose logs -f frontend
```

### Inspect Container Health:
```bash
docker compose ps
```

### Stop Services:
```bash
docker compose down
```

### Stop and Remove Volumes (Caution: Clears in-container state):
```bash
docker compose down -v
```

---

## ⚙️ Custom Configuration (`.env`)

You can pass an environment file to customize behavior:

```env
# Optional External Relational Database
DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/enterprise_db
DB_ALLOWED_TABLES=urunler,satislar,destek_talepleri

# API Limits
MAX_UPLOAD_SIZE_MB=50
LOG_LEVEL=INFO
```

Apply environment variables automatically by placing a `.env` file in the project root alongside `docker-compose.yml`.

---

## 🛠️ Troubleshooting

### 1. NVIDIA Container Toolkit Verification:
To confirm GPU passthrough is functional on your Docker host:
```bash
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
```

### 2. Port Conflicts:
If port `8000` or `8501` is already in use on your host machine, update the port mapping in `docker-compose.yml`:
```yaml
ports:
  - "8080:8000"  # Changes host port to 8080
```
