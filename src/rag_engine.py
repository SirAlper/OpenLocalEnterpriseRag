import os
import torch
from sentence_transformers import SentenceTransformer
import chromadb
from src.config import EMBEDDING_MODEL_NAME, VECTOR_DB_PATH


class RAGEngine:
    def __init__(self):
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Embedding modeli ({device}) üzerinde yükleniyor...")
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME, device=device)

        print("Yerel Vektör Veritabanı (ChromaDB) başlatılıyor...")
        self.client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
        self.collection = self.client.get_or_create_collection(name="enterprise_docs")

    def add_documents(self, documents: list[str], ids: list[str], metadatas: list[dict] = None):
        """Yeni belgeleri vektörleştirip veritabanına ekler."""
        if not documents:
            print("Eklenecek belge bulunamadı.")
            return

        embeddings = self.embedding_model.encode(documents, show_progress_bar=True).tolist()

        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas
        )
        print(f"Toplam {len(documents)} parça başarıyla indekslendi.")

    def delete_document(self, filename: str) -> int:
        """Belirtilen kaynağa ait tüm parçaları ChromaDB'den siler."""
        try:
            results = self.collection.get(where={"source": filename})
            ids = results.get("ids", [])
            if ids:
                self.collection.delete(ids=ids)
                print(f"'{filename}' dosyasına ait {len(ids)} parça ChromaDB'den silindi.")
                return len(ids)
            return 0
        except Exception as e:
            print(f"Silme işlemi sırasında hata: {e}")
            return 0

    def get_stats(self) -> dict:
        """Vektör veri tabanındaki genel istatistikleri döner."""
        total_chunks = self.collection.count()
        all_data = self.collection.get(include=["metadatas"])
        metadatas = all_data.get("metadatas", []) or []

        doc_counts = {}
        for meta in metadatas:
            if meta and "source" in meta:
                src = meta["source"]
                doc_counts[src] = doc_counts.get(src, 0) + 1

        return {
            "total_chunks": total_chunks,
            "total_documents": len(doc_counts),
            "document_chunks": doc_counts
        }

    def search(self, query: str, n_results: int = 3) -> dict:
        """Soruya en yakın şirket belgelerini ve kaynak metaverilerini bulur."""
        if self.collection.count() == 0:
            return {"context": "", "sources": []}

        # İstenen n_results, toplam parça sayısından fazla olamaz
        actual_n = min(n_results, self.collection.count())
        q_embedding = self.embedding_model.encode(query).tolist()
        results = self.collection.query(
            query_embeddings=[q_embedding],
            n_results=actual_n,
            include=["documents", "metadatas", "distances"]
        )

        retrieved_docs = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        sources = []
        for doc_text, meta, dist in zip(retrieved_docs, metadatas, distances):
            sources.append({
                "source": meta.get("source", "Bilinmeyen Belge") if meta else "Bilinmeyen Belge",
                "chunk_index": meta.get("chunk_index", 0) if meta else 0,
                "content": doc_text,
                "distance": round(float(dist), 4) if dist is not None else None
            })

        return {
            "context": "\n\n".join(retrieved_docs),
            "sources": sources
        }