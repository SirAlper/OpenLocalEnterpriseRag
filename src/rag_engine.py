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

    def search(self, query: str, n_results: int = 3) -> str:
        """Soruya en yakın şirket belgelerini bulur."""
        q_embedding = self.embedding_model.encode(query).tolist()
        results = self.collection.query(
            query_embeddings=[q_embedding],
            n_results=n_results
        )

        retrieved_docs = results.get("documents", [[]])[0]
        return "\n\n".join(retrieved_docs)