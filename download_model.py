import os
from huggingface_hub import snapshot_download
from src.config import MODELS_DIR, LOCAL_LLM_PATH, LOCAL_EMBEDDING_PATH

os.makedirs(MODELS_DIR, exist_ok=True)

models = [
    {
        "name": "1/2 - Embedding Modeli (Metin Vektörleştirici)",
        "repo_id": "sentence-transformers/all-MiniLM-L6-v2",
        "local_dir": LOCAL_EMBEDDING_PATH
    },
    {
        "name": "2/2 - Küçük Dil Modeli (SLM - Qwen2.5-1.5B-Instruct)",
        "repo_id": "Qwen/Qwen2.5-1.5B-Instruct",
        "local_dir": LOCAL_LLM_PATH
    }
]

for item in models:
    print(f"\nHazırlanıyor / İndiriliyor: {item['name']} -> {item['local_dir']}...")
    snapshot_download(
        repo_id=item["repo_id"],
        local_dir=item["local_dir"],
        resume_download=True
    )

print("\n Modeller başarıyla doğrudan './models' klasörüne sabitlendi! Artık temp/cache şişmesi olmadan çalışabilirsin.")