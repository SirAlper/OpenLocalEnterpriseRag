# 🏗️ System Architecture & Engineering Principles

`OpenLocalRagAgents` is built upon **Two-Stage Retrieval**, **Stateful Agentic AI (LangGraph)**, **Role-Based Access Control (RBAC)**, and **Tamper-Evident Audit Logging** workflows designed to execute 100% locally on private enterprise hardware without sending proprietary data to third-party cloud APIs.

---

## 📐 High-Level Architecture Diagram

```text
┌──────────────────────────────────────────────────────────────────────────────────┐
│                            Enterprise Client Layer                               │
│       Streamlit Enterprise UI (Port 8501)   │   External Workplace Apps / Bots   │
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │ HTTP REST (Bearer JWT)
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             FastAPI Gateway (Port 8000)                          │
│  ┌─────────────────────────┐  ┌────────────────────────┐  ┌───────────────────┐  │
│  │  CORS & Rate Protection │  │ JWT & RBAC Middleware  │  │ Structured Logger │  │
│  │  (Allowed Origins)      │  │ (admin/editor/viewer)  │  │ (src.core.logger) │  │
│  └─────────────────────────┘  └────────────────────────┘  └───────────────────┘  │
│  ┌────────────────────────────────────────────────────────────────────────────┐  │
│  │                    Query Concurrency Manager (State)                       │  │
│  │      HuggingFace: asyncio.Lock()  │  Ollama: asyncio.Semaphore(N)          │  │
│  └────────────────────────────────────────────────────────────────────────────┘  │
└───────────────────────┬──────────────────────────────────┬───────────────────────┘
                        │                                  │
      Workflow Dispatch │                Audit & ETL Event │
                        ▼                                  ▼
┌────────────────────────────────────────┐  ┌──────────────────────────────────────┐
│       LangGraph Workflow Engine        │  │     Data & Governance Layer          │
│                                        │  │                                      │
│  ┌───────────────┐   ┌──────────────┐  │  │  ┌────────────────────────────────┐  │
│  │ Retrieve Node │──>│Generate Node │  │  │  │ Audit Logger (data/audit.db)   │  │
│  └───────┬───────┘   └──────┬───────┘  │  │  │ (Tamper-evident query/auth log)│  │
│          │                  │          │  │  └────────────────────────────────┘  │
│          │                  ▼          │  │  ┌────────────────────────────────┐  │
│          │           ┌──────────────┐  │  │  │ Checkpointer (conversations.db)│  │
│          │     ┌────>│  Grade Node  │  │  │  │ (Session multi-turn memory)    │  │
│          │     │     └──────┬───────┘  │  │  └────────────────────────────────┘  │
│          │     │            │          │  │  ┌────────────────────────────────┐  │
│          │     │     Passed │ Speculative │  │ User Store (data/users.json)   │  │
│          │     │            ▼          │  │  │ (Bcrypt salted password hashes)│  │
│          │     │     ┌──────────────┐  │  │  └────────────────────────────────┘  │
│          │  Refine   │ Refine Node  │  │  │  ┌────────────────────────────────┐  │
│          │   Loop    │(Self-Correct)│  │  │  │ Universal DB Connector         │  │
│          │     │     └──────┬───────┘  │  │  │ (Postgres/MSSQL/MySQL/Oracle/  │  │
│          │     └────────────┘          │  │  │  SQLite Read-Only Guards)      │  │
│          │            Max retries      │  │  └────────────────────────────────┘  │
│          │                  ▼          │  └──────────────────────────────────────┘
│          │           ┌──────────────┐  │
│          │           │Fallback Node │──> [END]
│          │           └──────────────┘  │
│          │                  ▲          │
│          │      Grounded    │          │
│          └──────────────────┴──────────> [END]
└──────────────────────┬─────────────────┘
                       │
       Context Scoring │ Generation Call
                       ▼
┌────────────────────────────────────────┐  ┌──────────────────────────────────────┐
│         Knowledge Retrieval Layer      │  │          Dual LLM Serving            │
│                                        │  │                                      │
│  ┌──────────────────────────────────┐  │  │  [Option A: In-Process HuggingFace]  │
│  │ ChromaDB Vector Store            │  │  │  - Qwen2.5-1.5B-Instruct (BF16)      │
│  │ - BAAI/bge-m3 Dense Vectors      │  │  │  - Zero network overhead             │
│  │ - Contextual Chunking Headers    │  │  │                                      │
│  └──────────────────────────────────┘  │  │  [Option B: External Ollama Engine]  │
│  ┌──────────────────────────────────┐  │  │  - LangChain ChatOllama              │
│  │ Cross-Encoder Reranker           │  │  │  - Qwen2.5:7B / Llama3.1:8B          │
│  │ - BAAI/bge-reranker-v2-m3        │  │  │  - Parallel worker semaphore         │
│  └──────────────────────────────────┘  │  └──────────────────────────────────────┘
└────────────────────────────────────────┘
```

---

## 🔍 Two-Stage Retrieval & Cross-Encoder Reranking

Traditional naive RAG implementations rely solely on vector cosine similarity, which frequently retrieves semantically adjacent but factually unhelpful text passages. Our architecture addresses this with a high-accuracy two-stage pipeline:

### Stage 1: Fast Bi-Encoder Vector Search (`BAAI/bge-m3`)
* **Model:** `BAAI/bge-m3` (1024-dimensional dense vectors).
* **Operation:** User query is vectorized and matched against ChromaDB within milliseconds to retrieve a broad candidate pool (`n_results=10`).
* **Distance Thresholding:** Distant or irrelevant chunks exceeding `max_distance = 1.35` are discarded immediately.

### Stage 2: Full-Attention Cross-Encoder Reranking (`BAAI/bge-reranker-v2-m3`)
* **Model:** `BAAI/bge-reranker-v2-m3`.
* **Operation:** Remaining candidates are paired with the user query (`[Query, Document Chunk]`) and scored simultaneously across cross-attention layers.
* **Output:** Deep cross-attention scores determine genuine relevance. The top `RERANKER_TOP_N = 3` highest-scoring passages are selected and concatenated into the prompt context for the LLM.

---

## 📑 Contextual Chunking

Standard text splitters segment documents at fixed character or token boundaries. This often separates vital section clauses from their document titles or regulatory codes, eroding semantic retrieval accuracy.

The `src/rag/document_loader.py` module applies **Contextual Chunking**:
1. Scans the initial lines of the document to extract document titles and regulatory codes:
   - Example: `[Document: NovaTech Information Security Policy | CODE: SEC-POL-04]`
2. Automatically injects this contextual header **at the beginning of every chunk produced from that document**:
   ```text
   [Document: NovaTech Information Security Policy | CODE: SEC-POL-04]
   Clause 4.1: USB drive usage on corporate computers requires prior IT authorization...
   ```
3. The embedding model retains the parent document identity and regulatory scope for every individual passage during similarity search.

---

## 🧠 Multi-Turn Conversational Memory & Checkpointing

Conversations are statefully managed across turns without inflating prompt tokens or leaking context across users:

1. **SQLite Checkpointer (`data/conversations.db`):**
   - The LangGraph workflow is compiled with `SqliteSaver`, creating atomic checkpoint snapshots at each graph node.
   - Falls back gracefully to in-memory checkpointing if SQLite initialization encounters permission limits.
2. **User-Isolated Session Threads (`thread_id`):**
   - Thread keys are partitioned by username: `thread_id = f"{username}_{session_id}"`.
   - Ensures strict tenant isolation: users cannot observe or poison another employee's session state.
3. **Retrieval Query Context Enrichment:**
   - In `AgentNodes.retrieve()`, when multi-turn conversation history is detected, the search query is dynamically enriched with keywords from recent question turns:
     `search_query = f"{question} {recent_context}"`.
   - Enables intuitive follow-up queries (e.g., *"What were the exemptions?"* following a question about *"Password update policy"*).

---

## 🤖 LangGraph State Graph & Closed-Loop Self-Correction (Self-RAG)

Rather than executing as a rigid linear pipeline, the system operates as a feedback-driven state graph (`src/agent/agent_graph.py`):

1. **`retrieve` Node:**
   - Enriches query with conversation history, queries ChromaDB, and filters through the Cross-Encoder reranker.
   - If no relevant enterprise documents are found, immediately routes to the standard no-context response.
2. **`generate` Node:**
   - Invokes the active LLM backend (`ChatHuggingFace` or `ChatOllama`) to formulate a professional, grounded response adhering strictly to the retrieved context.
3. **`grade` Node (Hallucination Grader):**
   - Compares the draft response with the retrieved context. Paraphrasing and stylistic summaries are preserved; only unverified, contradictory, or fabricated claims trigger failure.
4. **Conditional Routing (`decide_hallucinate`):**
   - **Grounded (`yes`):** Workflow terminates successfully (`END`), returning the verified answer alongside chunk sources and distances.
   - **Ungrounded / Speculative (`no`):**
     - If the answer has not yet been refined (`retry_count < 1`), it routes to the **`refine`** node.
     - If retry limits are exceeded (`retry_count >= 1`), it routes to the safe `fallback` node.
5. **`refine` Node (Closed-Loop Self-Correction):**
   - Prunes unverified assertions, retains confirmed factual statements, and cleanly restructures the draft response.
   - **Re-Grading Loop:** Once refined, control automatically loops back to `grade` for a secondary audit. If the refined answer passes, it terminates to `END`; if speculative statements persist, it routes to `fallback`.
6. **User Interaction & Thinking Indicator:**
   - Eliminates progressive character streaming glitches. The UI displays an active thinking indicator while graph nodes execute, delivering the complete, validated response atomically.

---

## 🛡️ Enterprise Infrastructure & Security Architecture

### 1. Role-Based Access Control (RBAC) & Authentication
* **JWT Bearer Authentication:** Handled via `src/auth/jwt_handler.py` using HMAC-SHA256 tokens with configurable expiration (`ACCESS_TOKEN_EXPIRE_MINUTES`).
* **Bcrypt Password Hashing:** Salted hashes stored locally in `data/users.json`. Plaintext passwords are never persisted or logged.
* **Three-Tier Authorization Model:**
  * `admin`: Complete administrative privileges (user registration, account status/role editing, account deletion, database execution, table ETL sync, audit log inspection).
  * `editor`: Operational privileges (uploading files, deleting files, vectorization, running assistant queries).
  * `viewer`: Read-only access (asking questions, viewing public stats, inspecting database connection status).

### 2. Tamper-Evident Compliance Audit Trail (`src.core.audit`)
* **Structured SQLite Storage (`data/audit.db`):** Records every business event: user login, query, document upload, document deletion, database query, and ETL synchronization.
* **Metadata Captured:** Timestamp (ISO), username, role, action, target detail, sources cited, answer preview, client IP address, execution duration in milliseconds, and status (`success`, `error`, `denied`).
* **Zero Cloud Leakage:** Audit logs reside strictly on local storage; no telemetry or reporting metrics leave the network.

### 3. Dual LLM Serving & Adaptive Concurrency Protection
* **In-Process HuggingFace (`LLM_BACKEND=huggingface`):**
  - Model weights loaded directly in BF16 (~2.8 GB VRAM).
  - Serialized via `asyncio.Lock()` to prevent GPU VRAM collisions and transformers pipeline race conditions.
* **External Ollama Serving (`LLM_BACKEND=ollama`):**
  - Offloads generation to an external Ollama instance hosting larger models (`qwen2.5:7b`, `llama3.1:8b`).
  - Governed by `asyncio.Semaphore(OLLAMA_NUM_PARALLEL)` for multi-user parallel request processing.

### 4. File Upload Hardening & Path Traversal Prevention
* **Path Traversal Protection:** `os.path.basename()` and canonical directory resolution enforce strict sanitization against directory traversal vectors (e.g. `../../`).
* **Extension Whitelist:** Restricts uploads exclusively to `.pdf`, `.docx`, and `.txt` files. Executables or scripts (`.exe`, `.sh`, `.py`) are rejected with HTTP 400.
* **Streaming Memory Limit:** File uploads are validated in 1MB chunks up to `MAX_UPLOAD_SIZE_MB` (default 50 MB). Exceeding uploads are immediately purged from disk and return HTTP 413.

### 5. Database Isolation & Table Access Controls
* **Read-Only SQL Guards:** Queries are strictly validated to begin with `SELECT` or `WITH ... SELECT`, discarding any modification keywords (`DROP`, `DELETE`, `INSERT`, `UPDATE`, `ALTER`, etc.).
* **Table Whitelist Enforcement:** When `DB_ALLOWED_TABLES` is defined, `FROM` and `JOIN` clauses are parsed and verified. Unauthorized table access attempts are blocked before execution.
* **Max Rows Capping:** Result sets are capped at `DB_MAX_ROWS` to prevent memory exhaustion.

### 6. Centralized Logging Infrastructure (`src.core.logger`)
* Structured, leveled logging (`INFO`, `WARNING`, `ERROR`).
* Output is streamed to both the terminal and rotating disk log files (10 MB per file, 5 backup cycles) with sensitive user data omitted.
