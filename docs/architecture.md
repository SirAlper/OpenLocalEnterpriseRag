# 🏗️ System Architecture & Engineering Principles

`OpenLocalEnterpriseRag` is built upon **Two-Stage Retrieval** and **Stateful Agentic AI (LangGraph)** workflows designed to execute 100% locally on private enterprise hardware without sending proprietary data to third-party cloud APIs.

---

## 📐 High-Level Architecture Diagram

```text
+-------------------------------------------------------------------------+
|                              FastAPI Gateway                            |
|        (POST /api/v1/documents  |  POST /api/v1/query)                  |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                        LangGraph Workflow Engine                        |
|                                                                         |
|   +-------------------+                +------------------------+       |
|   |   Retrieve Node   | -------------> |    Generation Node     |       |
|   +---------+---------+                +-----------+------------+       |
|             |                                      |                    |
|             |                                      v                    |
|             |                 +--------------------+------------+       |
|             |                 |  +---------------------------+  |       |
|             |                 |  |    Hallucination Grader   |<----+    |
|             |                 |  +-------------+-------------+  |   |    |
|             |                 +----------------|----------------+   |    |
|             |                                  |                    |    |
|             |              +-------------------+------------------+ |    |
|             |              | [Verified Grounded]                  | |    |
|             |              v                                      | |    |
|             |            [END]                                    | |    |
|             |                                                     | |    |
|             |              | [Unverified & retry < 1]             | |    |
|             |              v                                      | |    |
|             |     +-------------------+                           | |    |
|             |     |    Refine Node    | --------------------------+ |    |
|             |     | (Self-Correction) | (Re-evaluates via Grader)   |    |
|             |     +-------------------+                             |    |
|             |                                                       |    |
|             |              | [Unverified & retry >= 1]              |    |
|             |              v                                        |    |
|             |     +-------------------+                             |    |
|             |     |   Fallback Node   | ------------------------> [END]  |
|             |     +-------------------+                                  |
+-------------|-----------------------------------------------------------+
              |
              v
+-----------------------------+     +-------------------------------+
|     ChromaDB Vector Store   |     |    CrossEncoder Reranker      |
|    (BAAI/bge-m3 Embeds)     |     |  (BAAI/bge-reranker-v2-m3)   |
+-----------------------------+     +-------------------------------+
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

## 🤖 LangGraph State Graph & Self-Correction (Self-RAG)

Rather than executing as a rigid linear pipeline, the system operates as a feedback-driven state graph (`src/agent/agent_graph.py`):

1. **`retrieve` Node:**
   - Queries ChromaDB and filters through the Cross-Encoder reranker.
   - If no relevant enterprise documents are found, immediately routes to the standard no-context response.
2. **`generate` Node:**
   - Invokes `Qwen2.5-1.5B-Instruct` to formulate a professional, grounded response adhering strictly to the retrieved context.
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
   - Eliminates progressive character streaming glitches. The UI displays an active *"💭 Thinking and reviewing enterprise documents..."* spinner while graph nodes execute, delivering the complete, validated response atomically.

---

## 🛡️ Enterprise Infrastructure & Security Architecture

The platform implements defense-in-depth security and scalable infrastructure controls across the application stack:

### 1. Concurrency & Thread-Safety (`asyncio.Lock`)
* **Serialization:** Concurrent user requests at `/api/v1/query` and `/api/v1/query-stream` are serialized via `asyncio.Lock()`.
* **Resource Protection:** Prevents concurrent GPU memory thrashing, race conditions in transformers execution pipelines, and ChromaDB SQLite lock contention.

### 2. Lifespan Management (FastAPI `lifespan`)
* Heavy ML models (`SentenceTransformer`, `CrossEncoder`, `ChatHuggingFace`) are initialized during server startup within `@asynccontextmanager async def lifespan(app)`.
* Eliminates cold-start penalties on individual API calls while keeping unit test suites lightweight and isolated.

### 3. File Upload Hardening & Path Traversal Prevention
* **Path Traversal Protection:** `os.path.basename()` enforces strict filename sanitization against directory traversal vectors (e.g. `../../`).
* **Extension Whitelist:** Restricts uploads exclusively to `.pdf`, `.docx`, and `.txt` files. All executable or script extensions (`.exe`, `.sh`, `.py`) are rejected with HTTP 400.
* **Streaming Memory Limit:** File uploads are validated in 1MB chunks up to `MAX_UPLOAD_SIZE_MB` (default 50 MB). Exceeding uploads are immediately purged from disk and return HTTP 413 (Payload Too Large).

### 4. Database Isolation & Table Access Controls
* **Read-Only Guards:** Queries are strictly validated to begin with `SELECT` or `WITH ... SELECT`, discarding any data modification keywords (`DROP`, `DELETE`, `INSERT`, etc.).
* **Table Whitelist Enforcement:** When `DB_ALLOWED_TABLES` is defined, `FROM` and `JOIN` clauses are parsed and verified. Unauthorized table access attempts are blocked before execution.

### 5. Centralized Logging Infrastructure (`src.core.logger`)
* Replaces unformatted console prints with structured, leveled logging (`INFO`, `WARNING`, `ERROR`).
* Output is streamed to both the terminal and rotating disk log files (10 MB per file, 5 backup cycles) with zero telemetry leakage.

