import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "models")
VECTOR_DB_PATH = os.path.join(BASE_DIR, "vector_db")
DOCS_PATH = os.path.join(BASE_DIR, "data")

LOCAL_LLM_PATH = os.path.join(MODELS_DIR, "qwen2.5-1.5b")
LOCAL_EMBEDDING_PATH = os.path.join(MODELS_DIR, "bge-m3")
LOCAL_RERANKER_PATH = os.path.join(MODELS_DIR, "bge-reranker-v2-m3")

# Yerel klasörde model varsa oradan oku, yoksa HuggingFace Hub adını kullan
LLM_MODEL_NAME = LOCAL_LLM_PATH if os.path.exists(LOCAL_LLM_PATH) else "Qwen/Qwen2.5-1.5B-Instruct"
EMBEDDING_MODEL_NAME = LOCAL_EMBEDDING_PATH if os.path.exists(LOCAL_EMBEDDING_PATH) else "BAAI/bge-m3"
RERANKER_MODEL_NAME = LOCAL_RERANKER_PATH if os.path.exists(LOCAL_RERANKER_PATH) else "BAAI/bge-reranker-v2-m3"

# Reranker sonrası LLM'e gönderilecek en alakalı parça sayısı
RERANKER_TOP_N = 3

os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Yalnızca tüm yerel modeller mevcutsa ve indirme modunda değilsek çevrimdışı modu etkinleştir
ALL_LOCAL_MODELS_EXIST = (
    os.path.exists(LOCAL_LLM_PATH)
    and os.path.exists(LOCAL_EMBEDDING_PATH)
    and os.path.exists(LOCAL_RERANKER_PATH)
)
if ALL_LOCAL_MODELS_EXIST and os.getenv("ALLOW_ONLINE_HF", "0") != "1":
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

# PyTorch 4-bit kuantizasyon ayarı (1.5B model BF16'da sadece 2.8GB VRAM tüketir, 4-bit Türkçe kalitesini bozduğu için False)
USE_4BIT_QUANTIZATION = False

# Embedding ve Reranker Cihazı:
# LLM tek başına GPU VRAM'e (~3 GB) tam sığsın ve VRAM aşımıyla Windows sanal bellek (pagefile) patlamasın diye
# Embedding ve Reranker sorgulamaları hafif olduğundan CPU üzerinde çalıştırılır.
RAG_DEVICE = os.getenv("RAG_DEVICE", "cpu")