# 🏢 OpenLocalEnterpriseRag

[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?logo=pytorch&logoColor=white)](https://pytorch.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agentic%20AI-blueviolet.svg)](https://langchain-ai.github.io/langgraph/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Privacy Protected](https://img.shields.io/badge/Privacy-100%25%20On--Premise-brightgreen.svg)](#)

> **A privacy-first, on-premise generative AI and Agentic RAG platform engineered to run 100% locally on your infrastructure. Prevents enterprise data leakage to third-party cloud providers (OpenAI, Anthropic, etc.) with zero external API dependencies.**

---

## ✨ Key Capabilities

* 🔒 **100% Local & Air-Gapped:** All embeddings, Cross-Encoder reranking, and LLM inferences execute strictly on your local GPU/CPU. Zero data egress, zero cloud telemetry, and zero token costs.
* 🎯 **Two-Stage Retrieval:** Combines `BAAI/bge-m3` dense vector search with `BAAI/bge-reranker-v2-m3` Cross-Encoder scoring to extract pinpoint enterprise context within milliseconds.
* 🛡️ **Self-Correcting Hallucination Guard (Self-RAG):** Evaluates draft answers against retrieved sources. If speculative claims are detected on complex queries, the `refine` node prunes hallucinations and preserves confirmed facts instead of abruptly failing.
* 🗄️ **Universal Database Connector:** Connects to **PostgreSQL, MSSQL, MySQL, Oracle, and SQLite** via an SQLAlchemy abstraction layer with strict read-only security guards and automated table vectorization.
* ⚡ **Thinking Indicator UX:** Streamlined user experience featuring interactive thinking indicators while LangGraph verifies claims, delivering complete, verified responses atomically without character flickering.
* 🌐 **Language-Agnostic & Multilingual:** Native multilingual search across enterprise corpora powered by BGE-M3 dense vectors, responding naturally in the user's language without artificial constraints.
* 🖥️ **Full-Stack Suite:** Ready-to-use FastAPI REST gateway (with Swagger OpenAPI docs) paired with a modern Streamlit enterprise control panel.

---

## 📚 Documentation Hub

Explore our detailed architectural and operational guides:

| Guide | Description |
| :--- | :--- |
| 🏗️ [**System Architecture**](docs/architecture.md) | LangGraph workflow engine, two-stage Cross-Encoder reranking, and contextual chunking |
| 📦 [**Installation & Hardware Matrix**](docs/installation.md) | VRAM/RAM hardware requirements, CUDA 12.1 setup, and offline model provisioning |
| 🗄️ [**Database Connectors**](docs/database_connectors.md) | Universal SQLAlchemy configurations, Text-to-SQL security, and ETL table vectorization |
| 🔌 [**REST API Reference**](docs/api_reference.md) | FastAPI endpoint documentation, NDJSON event streaming protocols, and cURL examples |
| 🐳 [**Docker Deployment**](docs/docker_deployment.md) | Production multi-service containerization, NVIDIA GPU passthrough, and volumes |
| 🗺️ [**Roadmap**](docs/roadmap.md) | Hybrid search (BM25 + Dense), GraphRAG, multi-turn memory, and vLLM acceleration |

---

## ⚡ Quickstart in 3 Steps

### 1. Clone Repository & Install Dependencies
```bash
git clone https://github.com/SirAlper/OpenLocalEnterpriseRag.git
cd OpenLocalEnterpriseRag

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\activate   # Linux/macOS: source .venv/bin/activate

# Install PyTorch (CUDA 12.1 recommended) and project requirements
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
```

### 2. Download Models Locally (One-time Setup)
Download model weights directly to `./models` to enable offline air-gapped inference:
```bash
python download_model.py
```

### 3. Launch Services
Run the backend and UI in separate terminal windows:

```bash
# Terminal 1: Backend API Gateway (FastAPI)
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
# Interactive Swagger Documentation: http://localhost:8000/docs

# Terminal 2: Enterprise Web Management UI (Streamlit)
streamlit run ui/app.py
# Web Dashboard: http://localhost:8501
```

### 4. Or Launch Instantly with Docker 🐳
Run the backend and UI with persistent local volumes:
```bash
# CPU Mode:
docker compose up -d

# NVIDIA GPU Mode (CUDA Passthrough):
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```
See the full [Docker Deployment Guide](docs/docker_deployment.md) for Container Toolkit setup.

### 5. Run Automated Tests
Verify all 32 unit and security tests across agent, database, loader, and API guards:
```bash
python -m unittest discover tests -v
# or using pytest:
pytest tests/ -v
```

---

## 📁 Repository Structure

```text
OpenLocalEnterpriseRag/
├── data/                  # Enterprise documents (PDF, DOCX, TXT) and sample SQLite DB
├── models/                # Local model weights (Qwen2.5-1.5B, BGE-M3, BGE-Reranker)
├── vector_db/             # ChromaDB persistent vector collection
├── tests/                 # Automated unit and security test suite (32 tests)
├── ui/
│   └── app.py             # Streamlit enterprise management dashboard & chat UI
├── src/
│   ├── core/              # System configurations, environment settings, and centralized logger
│   ├── rag/               # Contextual document loader and Two-Stage ChromaDB/Reranker engine
│   ├── agent/             # LangGraph state workflow, LLM loader, prompts, and tools
│   ├── connectors/        # SQLAlchemy universal database connector and table vectorizer
│   ├── api/               # Modular FastAPI REST API gateway (routes/, schemas, state)
│   └── main.py            # Backward-compatible launch entrypoint (uvicorn src.main:app)
├── docs/                  # [Comprehensive Technical Guides](docs/)
├── Dockerfile             # Production multi-stage Docker container specification
├── docker-compose.yml     # Multi-service compose definition (Backend + Frontend)
├── docker-compose.gpu.yml # NVIDIA GPU passthrough override
├── download_model.py      # Script to download HuggingFace model weights to local storage
├── requirements.txt       # Python package dependencies
└── LICENSE                # MIT License
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).