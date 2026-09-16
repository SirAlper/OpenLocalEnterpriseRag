import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODELS_DIR = os.path.join(BASE_DIR, "models")
VECTOR_DB_PATH = os.path.join(BASE_DIR, "vector_db")
DOCS_PATH = os.path.join(BASE_DIR, "data")

LOCAL_LLM_PATH = os.path.join(MODELS_DIR, "qwen2.5-1.5b")
LOCAL_EMBEDDING_PATH = os.path.join(MODELS_DIR, "bge-m3")
LOCAL_RERANKER_PATH = os.path.join(MODELS_DIR, "bge-reranker-v2-m3")

# Load from local folder if exists, otherwise fallback to HuggingFace Hub model ID
LLM_MODEL_NAME = LOCAL_LLM_PATH if os.path.exists(LOCAL_LLM_PATH) else "Qwen/Qwen2.5-1.5B-Instruct"
EMBEDDING_MODEL_NAME = LOCAL_EMBEDDING_PATH if os.path.exists(LOCAL_EMBEDDING_PATH) else "BAAI/bge-m3"
RERANKER_MODEL_NAME = LOCAL_RERANKER_PATH if os.path.exists(LOCAL_RERANKER_PATH) else "BAAI/bge-reranker-v2-m3"

# Number of top candidate chunks to pass to LLM after Cross-Encoder reranking
RERANKER_TOP_N = 3

os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Enable offline mode only if all local models exist and online download flag is not set
ALL_LOCAL_MODELS_EXIST = (
    os.path.exists(LOCAL_LLM_PATH)
    and os.path.exists(LOCAL_EMBEDDING_PATH)
    and os.path.exists(LOCAL_RERANKER_PATH)
)
if ALL_LOCAL_MODELS_EXIST and os.getenv("ALLOW_ONLINE_HF", "0") != "1":
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

# PyTorch 4-bit quantization setting (1.5B model in BF16 consumes only ~2.8GB VRAM)
USE_4BIT_QUANTIZATION = False

# Embedding and Reranker Device:
# Configured by default to CPU to keep full GPU VRAM available for the LLM
RAG_DEVICE = os.getenv("RAG_DEVICE", "cpu")

# ──────────────────────────── DATABASE CONNECTION (OPTIONAL) ────────────────────────────
# Example connections:
# - PostgreSQL: "postgresql+psycopg2://user:pass@localhost:5432/enterprise_db"
# - MSSQL: "mssql+pyodbc://user:pass@host:1433/db?driver=ODBC+Driver+17+for+SQL+Server"
# - MySQL: "mysql+pymysql://user:pass@localhost:3306/db"
# - SQLite: "sqlite:///./data/sample_enterprise.db"
# If left empty, database features are disabled and the system operates purely on file RAG.
SAMPLE_DB_PATH = os.path.join(DOCS_PATH, "sample_enterprise.db")
DEFAULT_SQLITE_URL = f"sqlite:///{SAMPLE_DB_PATH}"

DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_SQLITE_URL if os.path.exists(SAMPLE_DB_PATH) else "")
DB_ALLOWED_TABLES = [t.strip() for t in os.getenv("DB_ALLOWED_TABLES", "").split(",") if t.strip()]
DB_MAX_ROWS = int(os.getenv("DB_MAX_ROWS", "50"))
