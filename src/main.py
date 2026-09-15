"""Enterprise Local RAG API Entry Point.

Geriye dönük uyumluluk ve Uvicorn çalıştırma köprüsü:
    uvicorn src.main:app --reload
veya doğrudan modüler yoldan:
    uvicorn src.api.main:app --reload
"""
from src.api.main import app

if __name__ == "__main__":
    import uvicorn
    # Dosya yüklemelerinde sunucunun modeli bellekten düşürüp baştan yüklemesini önlemek için reload=False
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=False)