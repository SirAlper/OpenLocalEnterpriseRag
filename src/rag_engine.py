import os
import torch
from sentence_transformers import SentenceTransformer, CrossEncoder
import chromadb
from src.config import EMBEDDING_MODEL_NAME, RERANKER_MODEL_NAME, VECTOR_DB_PATH, RERANKER_TOP_N, RAG_DEVICE


class RAGEngine:
    def __init__(self):
        device = RAG_DEVICE
        print(f"[RAG Engine] Embedding ve Reranker '{device}' üzerinde çalıştırılıyor...")

        # Çok Dilli Embedding Modeli (BAAI/bge-m3)
        is_local_embed = os.path.exists(EMBEDDING_MODEL_NAME)
        print(f"Çok Dilli Embedding Modeli ({EMBEDDING_MODEL_NAME.split(os.sep)[-1]}) yükleniyor...")
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME, device=device, local_files_only=is_local_embed)

        # Reranker Modeli (BAAI/bge-reranker-v2-m3)
        is_local_reranker = os.path.exists(RERANKER_MODEL_NAME)
        print(f"Reranker Modeli ({RERANKER_MODEL_NAME.split(os.sep)[-1]}) yükleniyor...")
        self.reranker = CrossEncoder(
            RERANKER_MODEL_NAME,
            max_length=512,
            device=device,
            local_files_only=is_local_reranker
        )

        print("Yerel Vektör Veritabanı (ChromaDB) başlatılıyor...")
        self.client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
        self.collection = self.client.get_or_create_collection(name="enterprise_docs")

    def add_documents(self, documents: list[str], ids: list[str], metadatas: list[dict] = None):
        """Yeni belgeleri vektörleştirip veritabanına ekler."""
        if not documents:
            print("Eklenecek belge bulunamadı.")
            return

        embeddings = self.embedding_model.encode(documents, show_progress_bar=True).tolist()

        self.collection.upsert(
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

    def search(self, query: str, n_results: int = 10, max_distance: float = 1.35) -> dict:
        """Soruya en yakın şirket belgelerini bulur ve Reranker ile yeniden sıralayarak en alakalı parçaları döner.

        Arama Akışı:
        1. ChromaDB'den geniş aday havuzu çek (n_results=10).
        2. max_distance eşiğiyle ilk filtrelemeyi yap.
        3. Kalan adayları CrossEncoder (Reranker) ile soru-belge çifti olarak puanla.
        4. En yüksek puanlı RERANKER_TOP_N parçayı döndür.
        """
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

        docs_list = results.get("documents") or []
        metas_list = results.get("metadatas") or []
        dists_list = results.get("distances") or []

        retrieved_docs = docs_list[0] if docs_list else []
        metadatas = metas_list[0] if metas_list else []
        distances = dists_list[0] if dists_list else []

        # 1. Mesafe eşiğiyle ilk filtreleme
        candidates = []
        for doc_text, meta, dist in zip(retrieved_docs, metadatas, distances):
            dist_val = round(float(dist), 4) if dist is not None else None

            if dist_val is not None and max_distance is not None and dist_val > max_distance:
                continue

            candidates.append({
                "doc_text": doc_text,
                "meta": meta,
                "distance": dist_val
            })

        if not candidates:
            return {"context": "", "sources": []}

        # 2. Reranker ile yeniden puanlama
        pairs = [[query, c["doc_text"]] for c in candidates]
        reranker_scores = self.reranker.predict(pairs)
        if hasattr(reranker_scores, "tolist"):
            reranker_scores = reranker_scores.tolist()
        if isinstance(reranker_scores, (int, float)):
            reranker_scores = [reranker_scores]

        for candidate, score in zip(candidates, reranker_scores):
            candidate["reranker_score"] = round(float(score), 4)

        # 3. Reranker skoruna göre sırala ve en iyi RERANKER_TOP_N parçayı seç
        candidates.sort(key=lambda x: x["reranker_score"], reverse=True)
        top_candidates = candidates[:RERANKER_TOP_N]

        filtered_docs = []
        sources = []
        for c in top_candidates:
            filtered_docs.append(c["doc_text"])
            meta = c["meta"]
            sources.append({
                "source": meta.get("source", "Bilinmeyen Belge") if meta else "Bilinmeyen Belge",
                "chunk_index": meta.get("chunk_index", 0) if meta else 0,
                "content": c["doc_text"],
                "distance": c["distance"],
                "reranker_score": c["reranker_score"]
            })

        return {
            "context": "\n\n".join(filtered_docs),
            "sources": sources
        }