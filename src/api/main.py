import os
import shutil
import time
import json
import torch
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from pydantic import BaseModel
from src.rag.document_loader import DocumentLoader
from src.rag.rag_engine import RAGEngine
from src.agent.agent_graph import EnterpriseRAGAgent
from src.connectors.db_connector import DatabaseConnector, create_sample_sqlite_db
from src.connectors.db_loader import DatabaseTableLoader
from src.core.config import (
    DOCS_PATH,
    EMBEDDING_MODEL_NAME,
    LLM_MODEL_NAME,
    DATABASE_URL,
    SAMPLE_DB_PATH,
)

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

# Veritabanı bağlayıcısını başlat (eğer URL yoksa test için sample_enterprise.db hazırla)
if not DATABASE_URL and not os.path.exists(SAMPLE_DB_PATH):
    try:
        create_sample_sqlite_db(SAMPLE_DB_PATH)
    except Exception as e:
        print(f"[Sample DB] Örnek veritabanı oluşturulamadı: {e}")

db_connector = DatabaseConnector()
db_loader = DatabaseTableLoader(db_connector)


def auto_index_on_startup():
    """Sunucu başlarken data/ klasöründeki henüz indekslenmemiş belgeleri otomatik algılayıp ChromaDB'ye ekler."""
    if not os.path.exists(DOCS_PATH):
        os.makedirs(DOCS_PATH)
        return

    db_stats = rag_engine.get_stats()
    indexed_files = set(db_stats.get("document_chunks", {}).keys())

    supported_exts = {".pdf", ".docx", ".txt"}
    data_files = [
        f for f in os.listdir(DOCS_PATH)
        if os.path.isfile(os.path.join(DOCS_PATH, f)) and os.path.splitext(f)[1].lower() in supported_exts
    ]

    unindexed = [f for f in data_files if f not in indexed_files]

    if not unindexed:
        print(f"[Otomatik İndeksleme] data/ klasöründe indekslenmemiş belge yok. ({len(indexed_files)} belge zaten indeksli)")
        return

    print(f"[Otomatik İndeksleme] {len(unindexed)} yeni belge tespit edildi, indeksleniyor...")
    for filename in unindexed:
        file_path = os.path.join(DOCS_PATH, filename)
        chunks, ids, metadatas = document_loader.load_and_chunk_file(file_path)
        if chunks:
            rag_engine.add_documents(chunks, ids, metadatas)
            print(f"  ✓ '{filename}' → {len(chunks)} parça indekslendi.")
        else:
            print(f"  ✗ '{filename}' → ayrıştırılabilir metin bulunamadı.")

    print(f"[Otomatik İndeksleme] Tamamlandı!")


# Sunucu başlarken otomatik indekslemeyi çalıştır
auto_index_on_startup()


class QueryRequest(BaseModel):
    question: str


class SyncTableRequest(BaseModel):
    table_name: str
    text_columns: Optional[List[str]] = None
    title_column: Optional[str] = None
    id_column: Optional[str] = None


class TestQueryRequest(BaseModel):
    query: str


@app.get("/api/v1/stats", summary="Sistem ve Vektör Veritabanı İstatistikleri")
def get_system_stats():
    """Sistem donanımı, aktif modeller ve indeks istatistiklerini döner."""
    db_stats = rag_engine.get_stats()
    device = "CUDA (NVIDIA GPU)" if torch.cuda.is_available() else "CPU"
    db_conn_info = db_connector.test_connection()

    return {
        "status": "success",
        "device": device,
        "embedding_model": EMBEDDING_MODEL_NAME,
        "llm_model": LLM_MODEL_NAME,
        "total_chunks": db_stats["total_chunks"],
        "total_documents": db_stats["total_documents"],
        "documents": db_stats["document_chunks"],
        "database": db_conn_info
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

    # 3. Vektör tabanına yaz (Güncelleme durumunda önce eski parçaları temizle)
    rag_engine.delete_document(file.filename)
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


@app.get("/api/v1/database/status", summary="Veritabanı Bağlantı Durumu ve Şeması")
def get_database_status():
    """Veritabanı bağlantı durumunu, türünü ve erişilebilir tabloları döner."""
    conn_info = db_connector.test_connection()
    schema_summary = db_connector.get_schema_summary() if db_connector.is_connected else ""
    return {
        "status": "success",
        "connection": conn_info,
        "schema_summary": schema_summary
    }


@app.post("/api/v1/database/test-query", summary="Güvenli Salt-Okunur SQL Çalıştır")
def run_database_query(req: TestQueryRequest):
    """Yalnızca SELECT sorguları çalıştırır, güvenlik kurallarına uymayanları engeller."""
    result = db_connector.execute_query(req.query)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return {"status": "success", "data": result}


@app.post("/api/v1/database/sync-table", summary="Veritabanı Tablosunu Vektör İndeksine Aktar")
def sync_database_table(req: SyncTableRequest):
    """Belirtilen tablodaki satırları metin parçalarına dönüştürüp ChromaDB'ye indeksler."""
    if not db_connector.is_connected:
        raise HTTPException(status_code=400, detail="Veritabanı bağlantısı aktif değil.")

    chunks, ids, metadatas = db_loader.load_table_as_chunks(
        table_name=req.table_name,
        text_columns=req.text_columns,
        title_column=req.title_column,
        id_column=req.id_column
    )

    if not chunks:
        return {
            "status": "warning",
            "message": f"'{req.table_name}' tablosunda aktarılacak satır bulunamadı.",
            "chunk_count": 0
        }

    # Eski tablo kayıtlarını temizle ve yenilerini ekle
    rag_engine.delete_document(f"db_{req.table_name}")
    rag_engine.add_documents(chunks, ids, metadatas)

    return {
        "status": "success",
        "message": f"'{req.table_name}' tablosundaki {len(chunks)} kayıt başarıyla vektörleştirildi.",
        "table_name": req.table_name,
        "chunk_count": len(chunks)
    }


if __name__ == "__main__":
    import uvicorn
    # Dosya yüklemelerinde sunucunun modeli bellekten düşürüp baştan yüklemesini önlemek için reload=False
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=False)
