# 🗺️ Project Roadmap

The strategic development roadmap for `OpenLocalEnterpriseRag` is structured below to expand its capabilities as a world-class on-premise enterprise AI infrastructure.

---

## 🔍 1. Advanced Retrieval & Structured Ingestion

- [ ] **Hybrid Search (BM25 + Dense Vector with Reciprocal Rank Fusion):**
  - Merge semantic dense vector search with sparse keyword/code matching (BM25) via *Reciprocal Rank Fusion (RRF)* to achieve 100% precision on SKU codes and technical terminology.
- [ ] **Complex Table & Unstructured Document Parsing:**
  - Dedicated table segmentation and layout-aware chunking for Excel (`.xlsx`), CSV, and complex multi-column PDF reports.
- [ ] **Hierarchical & Parent-Child Chunking:**
  - Multi-tier indexing that performs granular vector search on small child chunks while providing parent contextual blocks to the LLM during generation.
- [ ] **Graph-Augmented RAG (GraphRAG):**
  - Transform enterprise entities and document relations into Knowledge Graphs for multi-hop causal reasoning and cross-departmental impact analysis.

---

## 🤖 2. Next-Gen Agentic RAG

- [ ] **Multi-Turn Conversational Memory (LangGraph Checkpointer):**
  - Integrate LangGraph Memory / SqliteSaver to persist conversation history and resolve references across multi-turn sessions.
- [ ] **Dynamic Query Rewriting & Expansion:**
  - Autonomous agent node to rewrite ambiguous user prompts into optimized search representations before querying the vector store.
- [x] **Closed-Loop Self-Correction & Refinement:**
  - Integrated `refine` node in LangGraph routed back to `grade` to audit refined responses, ensuring high factual fidelity.
- [x] **Universal Relational Database Connector & Text-to-SQL Tools:**
  - SQLAlchemy-based connector layer supporting PostgreSQL, MSSQL, MySQL, Oracle, and SQLite.
  - Strict read-only query guardrails, automatic `LIMIT` capping, and table whitelisting.
  - Table-to-vector ETL pipeline (`DatabaseTableLoader`) and agent tools (`sql_db_query`, `sql_db_schema`).
- [ ] **Multi-Agent Supervisor Teams:**
  - Supervisor pattern to route queries dynamically across specialized agents (Documentation Agent, SQL Data Agent, Mathematical Analyst).
- [ ] **User Feedback Loop:**
  - Thumbs up/down feedback widget in Streamlit UI to track and log answer ground truth metrics.

---

## ⚡ 3. Serving Optimization & Inference Acceleration

- [x] **Request Serialization & Concurrency Protection:**
  - Integrated `asyncio.Lock` to serialize LLM queries, avoiding GPU VRAM thrashing and pipeline race conditions under concurrent access.
- [ ] **Optimized Inference Engine Integration (vLLM / llama.cpp):**
  - Continuous batching and PagedAttention to maximize throughput and concurrency on GPU clusters.
- [ ] **Semantic Vector Caching:**
  - Cache recurring queries using vector similarity (Redis / GPTCache) to answer repeated enterprise questions with near-zero latency.
- [ ] **Speculative Decoding:**
  - Accelerate local LLM token generation using small draft models.

---

## 🏢 4. Enterprise Security, Governance & DevOps

- [x] **Automated Testing Suite (32 Tests):**
  - Unit and integration tests covering LangGraph decision branches, read-only SQL guards, file upload security, and contextual document loader.
- [x] **Defense-in-Depth API Security:**
  - Path traversal protection, file extension whitelisting, upload size limits, and configurable CORS origins.
- [x] **Centralized Logging & Lifespan Architecture:**
  - Standardized logger with console and rotating file handlers (`src.core.logger`), `.env` support, and FastAPI lifespan model loading.
- [ ] **Role-Based Access Control (RBAC):**
  - Enforce user and departmental permissions (HR, Legal, Finance, Engineering) at the ChromaDB collection and document levels.
- [ ] **Observability & Tracing:**
  - OpenTelemetry, Langfuse, or Arize Phoenix integration to trace latency, token consumption, and retrieval fidelity.
- [ ] **One-Command Containerization (Docker & NVIDIA Container Toolkit):**
  - Production-ready Dockerfile and docker-compose configurations with GPU passthrough for automated server provisioning.
- [ ] **Enterprise SSO & Directory Integration:**
  - SAML 2.0 / OAuth2 integration with Active Directory, Okta, and Keycloak for enterprise-grade authentication.
