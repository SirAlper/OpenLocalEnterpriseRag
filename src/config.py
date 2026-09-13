import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "models")
VECTOR_DB_PATH = os.path.join(BASE_DIR, "vector_db")
DOCS_PATH = os.path.join(BASE_DIR, "data")

LOCAL_LLM_PATH = os.path.join(MODELS_DIR, "qwen2.5-1.5b")
LOCAL_EMBEDDING_PATH = os.path.join(MODELS_DIR, "all-MiniLM-L6-v2")

# Yerel klasörde model varsa oradan oku, yoksa HuggingFace Hub adını kullan
LLM_MODEL_NAME = LOCAL_LLM_PATH if os.path.exists(LOCAL_LLM_PATH) else "Qwen/Qwen2.5-1.5B-Instruct"
EMBEDDING_MODEL_NAME = LOCAL_EMBEDDING_PATH if os.path.exists(LOCAL_EMBEDDING_PATH) else "all-MiniLM-L6-v2"

# PyTorch 4-bit kuantizasyon ayarı
USE_4BIT_QUANTIZATION = True