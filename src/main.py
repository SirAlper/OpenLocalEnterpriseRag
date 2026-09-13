import os
import shutil
import time
import json
import torch
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.document_loader import DocumentLoader
from src.rag_engine import RAGEngine
from src.agent_graph import EnterpriseRAGAgent
from src.config import DOCS_PATH, EMBEDDING_MODEL_NAME, LLM_MODEL_NAME

app = FastAPI(
    title="Enterprise Local RAG API",
    description="Bulut bağımlılığı olmayan, veri gizliliği odaklı yerel RAG ve Ajan sistemi.",
    version="1.1.0"
)

# CORS ayarları (Streamlit veya Web arayüzünden doğrudan erişim için)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servisleri başlat
rag_engine = RAGEngine()
agent = EnterpriseRAGAgent(rag_engine)
document_loader = DocumentLoader(DOCS_PATH)


class QueryRequest(BaseModel):
    question: str


@app.get("/api/v1/stats", summary="Sistem ve Vektör Veritabanı İstatistikleri")
def get_system_stats():
    """Sistem donanımı, aktif modeller ve indeks istatistiklerini döner."""
    db_stats = rag_engine.get_stats()
    device = "CUDA (NVIDIA GPU)" if torch.cuda.is_available() else "CPU"
    
    return {
        "status": "success",
        "device": device,
        "embedding_model": EMBEDDING_MODEL_NAME,
        "llm_model": LLM_MODEL_NAME,
        "total_chunks": db_stats["total_chunks"],
        "total_documents": db_stats["total_documents"],
        "documents": db_stats["document_chunks"]
    }


@app.get("/api/v1/documents", summary="İndekslenmiş ve Yüklü Belgeleri Listele")
def list_documents():
    """data/ dizinindeki dosyaları ve vektör tabanındaki parça sayılarını listeler."""
    if not os.path.exists(DOCS_PATH):
        os.makedirs(DOCS_PATH)

    db_stats = rag_engine.get_stats()
    chunk_map = db_stats.get("document_chunks", {})

    files = []
    for filename in os.listdir(DOCS_PATH):
        file_path = os.path.join(DOCS_PATH, filename)
        if os.path.isfile(file_path):
            stat = os.stat(file_path)
            files.append({
                "filename": filename,
                "size_kb": round(stat.st_size / 1024, 2),
                "chunk_count": chunk_map.get(filename, 0),
                "modified_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime))
            })

    return {"status": "success", "count": len(files), "documents": files}


@app.delete("/api/v1/documents/{filename}", summary="Belgeyi ve Vektör İndeksini Sil")
def delete_document(filename: str):
    """Belirtilen dosyayı hem data/ klasöründen hem de ChromaDB'den tamamen siler."""
    file_path = os.path.join(DOCS_PATH, filename)
    file_deleted = False

    if os.path.exists(file_path):
        os.remove(file_path)
        file_deleted = True

    deleted_chunks = rag_engine.delete_document(filename)

    if not file_deleted and deleted_chunks == 0:
        raise HTTPException(status_code=404, detail=f"'{filename}' bulunamadı.")

    return {
        "status": "success",
        "message": f"'{filename}' başarıyla silindi.",
        "deleted_chunks": deleted_chunks,
        "file_deleted": file_deleted
    }


@app.post("/api/v1/upload-file", summary="Sisteme PDF veya Belge Yükle")
async def upload_file(file: UploadFile = File(...)):
    """Yeni bir belge yükler, parçalar ve ChromaDB'ye indeksler."""
    if not os.path.exists(DOCS_PATH):
        os.makedirs(DOCS_PATH)

    # 1. Dosyayı data/ dizinine kaydet
    file_path = os.path.join(DOCS_PATH, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 2. Sadece yüklenen tek dosyayı oku ve parçala (Artımlı İndeksleme)
    chunks, ids, metadatas = document_loader.load_and_chunk_file(file_path)

    if not chunks:
        return {
            "status": "warning",
            "message": f"'{file.filename}' yüklendi fakat ayrıştırılabilir metin bulunamadı.",
            "chunk_count": 0
        }

    # 3. Vektör tabanına yaz
    rag_engine.add_documents(chunks, ids, metadatas)

    return {
        "status": "success",
        "message": f"'{file.filename}' başarıyla yüklendi ve indekslendi.",
        "filename": file.filename,
        "chunk_count": len(chunks)
    }


@app.post("/api/v1/query", summary="Yapay Zekaya Soru Sor")
def query_rag(request: QueryRequest):
    """RAG Ajanı üzerinden soruya cevap ve referans kaynakları döner."""
    try:
        print(f"Kullanıcı sorusu: {request.question}")
        result = agent.query(request.question)
        return {
            "status": "success",
            "answer": result["answer"],
            "sources": result["sources"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/query-stream", summary="Yapay Zekaya Soru Sor (Canlı Akış / Streaming)")
def query_rag_stream(request: QueryRequest):
    """RAG Ajanı üzerinden kaynakları ve üretilen token'ları anlık akış (ndjson) olarak iletir."""
    try:
        print(f"Canlı akış kullanıcı sorusu: {request.question}")

        def event_generator():
            for event in agent.stream_events(request.question):
                yield json.dumps(event, ensure_ascii=False) + "\n"

        return StreamingResponse(event_generator(), media_type="application/x-ndjson")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)