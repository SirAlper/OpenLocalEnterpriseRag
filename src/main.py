import os
import shutil
from fastapi import FastAPI, HTTPException, UploadFile, File
from src.document_loader import DocumentLoader
from pydantic import BaseModel
from src.rag_engine import RAGEngine
from src.agent_graph import EnterpriseRAGAgent
from src.config import DOCS_PATH

app = FastAPI(
    title="Enterprise Local RAG API",
    description="Bulut bağımlılığı olmayan, veri gizliliği odaklı yerel RAG sistemi.",
    version="1.0.0"
)

# Servisleri başlat
rag_engine = RAGEngine()
agent = EnterpriseRAGAgent(rag_engine)

class QueryRequest(BaseModel):
    question: str

class DocumentRequest(BaseModel):
    texts: list[str]
    ids: list[str]

@app.post("/api/v1/query", summary="Yapay Zekaya Soru Sor")
def query_rag(request: QueryRequest):
    try:
        print("ajan dusunmeye basladi")
        answer = agent.query(request.question)
        print("dusunme islemi bitti")
        return {"status": "success", "answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/upload-file", summary="Sisteme PDF veya Belge Yükle")
async def upload_file(file: UploadFile = File(...)):
    # 1. Dosyayı data/ dizinine kaydet
    file_path = os.path.join(DOCS_PATH, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 2. Yüklenen dosyayı oku ve parçala
    loader = DocumentLoader(DOCS_PATH)
    chunks, ids, metadatas = loader.load_and_chunk_all()

    # 3. Vektör tabanına yaz
    rag_engine.add_documents(chunks, ids, metadatas)

    return {
        "status": "success",
        "message": f"'{file.filename}' başarıyla yüklendi ve indekslendi."
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)