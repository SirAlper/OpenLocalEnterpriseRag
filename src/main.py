from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.rag_engine import RAGEngine
from src.agent_graph import EnterpriseRAGAgent

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
        answer = agent.query(request.question)
        return {"status": "success", "answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/documents", summary="Veritabanına Belge Ekle")
def add_documents(request: DocumentRequest):
    try:
        rag_engine.add_documents(request.texts, request.ids)
        return {"status": "success", "message": f"{len(request.texts)} belge eklendi."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)