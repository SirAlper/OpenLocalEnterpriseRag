import os

# Enable Hugging Face Hub online access for model downloading
os.environ["ALLOW_ONLINE_HF"] = "1"
os.environ["HF_HUB_OFFLINE"] = "0"
os.environ["TRANSFORMERS_OFFLINE"] = "0"

from huggingface_hub import snapshot_download
from src.core.config import MODELS_DIR, LOCAL_LLM_PATH, LOCAL_EMBEDDING_PATH, LOCAL_RERANKER_PATH

os.makedirs(MODELS_DIR, exist_ok=True)

models = [
    {
        "name": "1/3 - Multilingual Embedding Model (BAAI/bge-m3)",
        "repo_id": "BAAI/bge-m3",
        "local_dir": LOCAL_EMBEDDING_PATH
    },
    {
        "name": "2/3 - Cross-Encoder Reranker Model (BAAI/bge-reranker-v2-m3)",
        "repo_id": "BAAI/bge-reranker-v2-m3",
        "local_dir": LOCAL_RERANKER_PATH
    },
    {
        "name": "3/3 - Small Language Model (SLM - Qwen2.5-1.5B-Instruct)",
        "repo_id": "Qwen/Qwen2.5-1.5B-Instruct",
        "local_dir": LOCAL_LLM_PATH
    }
]

if __name__ == "__main__":
    for item in models:
        print(f"\nDownloading / Verifying: {item['name']} -> {item['local_dir']}...")
        snapshot_download(
            repo_id=item["repo_id"],
            local_dir=item["local_dir"],
            resume_download=True,
            ignore_patterns=["*.onnx", "*.onnx_data", "onnx/*", "imgs/*", "*.jpg", "*.png"]
        )

    print("\nModels successfully saved to './models' directory! The system can now run in offline/air-gapped mode.")