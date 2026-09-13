from huggingface_hub import snapshot_download

models = [
    {
        "name": "1/2 - Embedding Modeli (Metin Vektörleştirici)",
        "repo_id": "sentence-transformers/all-MiniLM-L6-v2"
    },
    {
        "name": "2/2 - Küçük Dil Modeli (SLM - Qwen2.5-1.5B-Instruct)",
        "repo_id": "Qwen/Qwen2.5-1.5B-Instruct"
    }
]

for item in models:
    print(f"\nİndiriliyor: {item['name']}...")
    snapshot_download(
        repo_id=item["repo_id"],
        resume_download=True
    )

print("\n İki model de başarıyla yerel önbelleğe indirildi! Artık src/main.py dosyasını başlatabilirsin.")