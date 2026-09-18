# 🗺️ Project Roadmap

The strategic development roadmap for `OpenLocalRagAgents` is structured below to expand its capabilities as a world-class on-premise enterprise AI infrastructure.

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

- [x] **Multi-Turn Conversational Memory (LangGraph Checkpointer):**
  - Integrated LangGraph SQLite checkpointer (`conversations.db`) and session-based thread tracking (`thread_id`).
  - Contextual retrieval query enrichment and conversational history retention across turns.
- [ ] **Dynamic Query Rewriting & Expansion:**
  - Autonomous agent node to rewrite ambiguous user prompts into optimized search representations before querying the vector store.
- [x] **Closed-Loop Self-Correction & Refinement:**
  - Integrated `refine` node in LangGraph routed back to `grade` to audit refined responses, ensuring high factual fidelity.
- [x] **Universal Relational Database Connector & Text-to-SQL Tools:**
  - SQLAlchemy-based connector layer supporting PostgreSQL, MSSQL, MySQL, Oracle, and SQLite.
  - Strict read-only query guardrails, automatic `LIMIT` capping, and table whitelisting.
  - Table-to-vector ETL pipeline (`DatabaseTableLoader`) and agent tools (`sql_db_query`, `sql_db_schema`).
- [ ] **Multi-Agent Supervisor Teams (Upcoming):**
  - Supervisor pattern to route queries dynamically across specialized agents (Documentation Agent, SQL Data Agent).
- [ ] **User Feedback Loop:**
  - Thumbs up/down feedback widget in Streamlit UI to track and log answer ground truth metrics.

---

## ⚡ 3. Serving Optimization & Inference Acceleration

- [x] **Request Serialization & Concurrency Protection:**
  - Integrated `QueryConcurrencyManager` with dual-mode support: serialized `asyncio.Lock` for in-process HuggingFace, and parallel `asyncio.Semaphore` for Ollama serving.
- [x] **Optimized Inference Engine Integration (Ollama / vLLM):**
  - First-class Ollama support with `langchain-ollama` (`LLM_BACKEND=ollama`), enabling 7B/14B models (`qwen2.5:7b`, `llama3.1:8b`) and multi-request parallel processing.
  - Optional `ollama` container definition in `docker-compose.yml`.
- [ ] **Semantic Vector Caching:**
  - Cache recurring queries using vector similarity (Redis / GPTCache) to answer repeated enterprise questions with near-zero latency.
- [ ] **Speculative Decoding:**
  - Accelerate local LLM token generation using small draft models.

---

## 🏢 4. Enterprise Security, Governance & DevOps

- [x] **Automated Testing Suite (52 Tests):**
  - Comprehensive unit and integration tests covering LangGraph decision branches, read-only SQL guards, file upload security, authentication/RBAC, multi-turn memory, Ollama serving, resource stability, and audit trail logging.
- [x] **Defense-in-Depth API Security:**
  - Path traversal protection, file extension whitelisting, upload size limits, and configurable CORS origins.
- [x] **Centralized Logging & Lifespan Architecture:**
  - Standardized logger with console and rotating file handlers (`src.core.logger`), `.env` support, and FastAPI lifespan model loading.
- [x] **Role-Based Access Control (RBAC) & JWT Authentication:**
  - Native JWT Bearer token generation, bcrypt password hashing, and user role enforcement (`admin`, `editor`, `viewer`).
  - Permission-gated endpoints for document management, database queries, and user administration.
- [x] **Enterprise Audit Trail & Compliance Logging:**
  - Structured SQLite audit database (`data/audit.db`) recording all queries, file uploads/deletions, logins, and anomalies with execution duration and client IP.
  - Admin compliance inspection dashboard and statistics in both REST API and Streamlit UI.
- [ ] **Observability & Tracing:**
  - OpenTelemetry, Langfuse, or Arize Phoenix integration to trace latency, token consumption, and retrieval fidelity.
- [x] **One-Command Containerization (Docker & NVIDIA Container Toolkit):**
  - Production-ready Dockerfile and docker-compose configurations with GPU passthrough for automated server provisioning.
- [ ] **Enterprise SSO & Directory Integration:**
  - SAML 2.0 / OAuth2 integration with Active Directory, Okta, and Keycloak for enterprise-grade authentication.
