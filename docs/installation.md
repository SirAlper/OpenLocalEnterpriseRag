# 📦 Installation & Hardware Guide

This guide provides step-by-step instructions for deploying `OpenLocalEnterpriseRag` on local workstations or enterprise on-premise servers with hardware acceleration.

---

## 💻 System & Hardware Requirements

The system is engineered to run the multilingual embedding model, Cross-Encoder reranker, and Qwen2.5-1.5B concurrently with optimal memory allocation:

| Component | Minimum Requirements | Recommended Enterprise Setup |
| :--- | :--- | :--- |
| **Operating System** | Ubuntu 22.04 LTS / Windows 11 | Ubuntu 22.04 LTS / Windows 11 / RHEL 9 |
| **Python** | 3.10+ | 3.11 or 3.12 |
| **System RAM** | 8 GB DDR4 | 16 GB+ RAM |
| **GPU / VRAM** | NVIDIA GPU (**Min 4-6 GB VRAM**) | NVIDIA RTX 3060 / 4060 / A4000+ (8+ GB VRAM) |
| **CUDA Version** | CUDA 11.8+ | CUDA 12.1+ |

> **Memory Allocation Architecture:**  
> - `bge-m3` Embedding Model: ~1.1 GB (Runs on CPU to preserve GPU memory)  
> - `bge-reranker-v2-m3` Reranker Model: ~1.1 GB (Runs on CPU)  
> - `Qwen2.5-1.5B-Instruct` LLM: ~2.8 GB (Loaded directly into GPU VRAM in BF16 format)  
> - **Total GPU VRAM Footprint: ~3 GB!** (If no NVIDIA GPU is detected, the entire pipeline falls back to CPU execution).

---

## 🛠️ Step-by-Step Installation

### 1. Clone the Repository
```bash
git clone https://github.com/SirAlper/OpenLocalEnterpriseRag.git
cd OpenLocalEnterpriseRag
```

### 2. Create and Activate Virtual Environment
```bash
# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate

# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\activate
```

### 3. Install PyTorch with Hardware Acceleration (CUDA)

> **Important:** To leverage GPU acceleration, install PyTorch matching your CUDA version from the official PyTorch index:

* **NVIDIA GPU (CUDA 12.1 - Recommended):**
  ```bash
  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
  ```

* **NVIDIA GPU (CUDA 11.8):**
  ```bash
  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
  ```

* **CPU-Only (Testing / Development without GPU):**
  ```bash
  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
  ```

### 4. Install Project Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 📥 Provisioning Models Locally (`download_model.py`)

To prevent runtime downloads and avoid inflating `~/.cache` or OS temp directories, model weights are pinned directly into the project's `./models/` directory.

Run the provisioning script once:
```bash
python download_model.py
```

This script downloads:
1. `models/bge-m3`: Multilingual semantic dense vector model (~1.1 GB)
2. `models/bge-reranker-v2-m3`: Cross-Encoder reranker model (~1.1 GB)
3. `models/qwen2.5-1.5b`: Qwen 2.5 1.5B Instruct model (~2.8 GB)

Once downloaded, the system runs in **100% offline (air-gapped)** mode.

---

## 🚀 Launching Services

### Backend (FastAPI Gateway):
```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```
* **Interactive Swagger Documentation:** `http://localhost:8000/docs`

### Frontend (Streamlit Dashboard):
In a separate terminal window:
```bash
streamlit run ui/app.py
```
* **Web UI:** `http://localhost:8501`
