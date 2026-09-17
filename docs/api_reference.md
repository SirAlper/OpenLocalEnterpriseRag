# 🔌 REST API Documentation

`OpenLocalEnterpriseRag` exposes a high-performance REST API built on **FastAPI** to enable turnkey integration with enterprise portals, CRM, ERP, and internal workplace bots.

The interactive OpenAPI Swagger UI is available at `http://localhost:8000/docs` whenever the server is running.

---

## 📋 Endpoints Overview

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/stats` | Hardware (CUDA/CPU), model paths, and vector store statistics |
| `GET` | `/api/v1/documents` | List uploaded and indexed enterprise documents |
| `POST` | `/api/v1/upload-file` | Upload new PDF, DOCX, or TXT document and auto-index |
| `DELETE` | `/api/v1/documents/{filename}` | Permanently delete document from disk and vector store |
| `POST` | `/api/v1/query` | Batch question answering with verified sources and audit state |
| `POST` | `/api/v1/query-stream` | Stage event streaming (NDJSON protocol) with final answer |
| `GET` | `/api/v1/database/status` | Database connection status, dialect type, and schema summary |
| `POST` | `/api/v1/database/test-query` | Execute safe read-only SELECT queries |
| `POST` | `/api/v1/database/sync-table` | Convert database table into ChromaDB vector chunks |

---

## 📖 Endpoint Details & cURL Examples

### 1. System Statistics (`GET /api/v1/stats`)
Returns hardware acceleration status, active embedding/LLM paths, and document counts.

```bash
curl -X GET "http://localhost:8000/api/v1/stats"
```

**Example Response:**
```json
{
  "status": "success",
  "device": "CUDA (NVIDIA GPU)",
  "embedding_model": ".../models/bge-m3",
  "llm_model": ".../models/qwen2.5-1.5b",
  "total_chunks": 42,
  "total_documents": 3,
  "database": {
    "status": "connected",
    "dialect": "sqlite",
    "table_count": 3
  }
}
```

---

### 2. Document Upload (`POST /api/v1/upload-file`)
Accepts multipart/form-data upload, saves the file to `data/`, generates contextual chunks, and stores embeddings in ChromaDB.

* **Supported Formats:** `.pdf`, `.docx`, `.txt` (All other extensions return HTTP 400).
* **Maximum Size:** Configurable via `MAX_UPLOAD_SIZE_MB` (Default: 50 MB; exceeding files return HTTP 413).
* **Security:** Hardened against path traversal (`os.path.basename()` enforces filename sanitization).

```bash
curl -X POST "http://localhost:8000/api/v1/upload-file" \
     -F "file=@NovaTech_Security_Policy.pdf"
```

**Example Success Response (HTTP 200):**
```json
{
  "status": "success",
  "message": "'NovaTech_Security_Policy.pdf' successfully uploaded and indexed.",
  "filename": "NovaTech_Security_Policy.pdf",
  "chunk_count": 14
}
```

**Error Responses:**
* `HTTP 400 Bad Request`: `{"detail": "Unsupported file extension '.exe'. Allowed: .docx, .pdf, .txt"}`
* `HTTP 413 Payload Too Large`: `{"detail": "File exceeds maximum allowed size of 50MB."}`

---

### 3. Document Deletion (`DELETE /api/v1/documents/{filename}`)
Permanently deletes the file from `data/` and purges its chunks from ChromaDB.

* **Security:** Validated against path traversal; requests referencing parent paths are rejected.

```bash
curl -X DELETE "http://localhost:8000/api/v1/documents/NovaTech_Security_Policy.pdf"
```

---

### 4. Query Assistant - Batch (`POST /api/v1/query`)
Executes the LangGraph workflow, returning the verified answer, reference sources, and refinement flags.

> **Concurrency Note:** Requests are serialized via `asyncio.Lock()` to prevent GPU VRAM collisions and HuggingFace pipeline race conditions.

```bash
curl -X POST "http://localhost:8000/api/v1/query" \
     -H "Content-Type: application/json" \
     -d '{
       "question": "What is the password update policy for workstations?"
     }'
```

**Example Response:**
```json
{
  "status": "success",
  "answer": "According to the company information security policy, passwords must be updated at least every 90 days.",
  "sources": [
    {
      "source": "NovaTech_Security_Policy.pdf",
      "chunk_index": 2,
      "content": "[Document: NovaTech Information Security | CODE: SEC-04]\nClause 3: User passwords must be updated every 90 days...",
      "distance": 0.421,
      "reranker_score": 4.812
    }
  ],
  "hallucination_grade": "yes",
  "is_refined": false
}
```

---

### 5. Query Assistant - Event Stream (`POST /api/v1/query-stream`)
Streams execution stages and delivers the final answer via newline-delimited JSON (**NDJSON**).

```bash
curl -X POST "http://localhost:8000/api/v1/query-stream" \
     -H "Content-Type: application/json" \
     -d '{
       "question": "How does the hardware failure support process work?"
     }'
```

**Event Types Delivered in Stream:**
1. `{"type": "status", "message": "🔍 Searching relevant enterprise documents...", "node": "retrieve"}`
2. `{"type": "sources", "sources": [...]}`
3. `{"type": "status", "message": "✍️ Preparing response...", "node": "generate"}`
4. `{"type": "status", "message": "🛡️ Verifying factual accuracy...", "node": "grade"}`
5. *(If ungrounded & retry < 1)* `{"type": "status", "message": "✍️ Re-evaluating and refining response to match documents...", "node": "refine"}`
6. *(Re-grading after refine)* `{"type": "status", "message": "🛡️ Verifying factual accuracy...", "node": "grade"}`
7. `{"type": "grade", "grade": "yes", "passed": true, "is_refined": true}`
8. `{"type": "done", "answer": "...", "sources": [...], "is_refined": true}`

---

## 🔒 CORS Configuration

CORS policies are controlled via the `CORS_ORIGINS` environment variable in `.env`:

```env
# Comma-separated list of allowed origins
CORS_ORIGINS=http://localhost:8501,http://127.0.0.1:8501
```

Credentials (`allow_credentials=True`), all methods, and all headers are supported for these trusted origins.
