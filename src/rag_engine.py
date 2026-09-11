import os
from sentence_transformers import SentenceTransformer
import chromadb
from src.config import EMBEDDING_MODEL_NAME, VECTOR_DB_PATH


class RAGEngine:
    def __init__(self):
        print("Embedding modeli yükleniyor...")
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME, device='cuda')

        print("Yerel Vektör Veritabanı (ChromaDB) başlatılıyor...")
        self.client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
        self.collection = self.client.get_or_create_collection(name="enterprise_docs")

    def add_documents(self, documents: list[str], ids: list[str]):
        """Yeni belgeleri vektörleştirip veritabanına ekler."""
        embeddings = self.embedding_model.encode(documents).tolist()
        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            ids=ids
        )

    def search(self, query: str, n_results: int = 3) -> str:
        """Soruya en yakın şirket belgelerini bulur."""
        q_embedding = self.embedding_model.encode(query).tolist()
        results = self.collection.query(
            query_embeddings=[q_embedding],
            n_results=n_results
        )

        retrieved_docs = results.get("documents", [[]])[0]
        return "\n\n".join(retrieved_docs)