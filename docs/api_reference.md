# 🔌 REST API Dokümantasyonu

`OpenLocalEnterpriseRag`, kurumsal ERP, CRM veya web portallarıyla kolayca entegre olabilmesi için **FastAPI** tabanlı yüksek performanslı bir REST API sunar.

Tüm uç noktaların etkileşimli Swagger dokümantasyonuna sunucu çalışırken `http://localhost:8000/docs` adresinden erişilebilir.

---

## 📋 Uç Noktalar Listesi

| Metot | Uç Nokta | Açıklama |
| :--- | :--- | :--- |
| `GET` | `/api/v1/stats` | Donanım (CUDA/CPU), model ve indeks istatistikleri |
| `GET` | `/api/v1/documents` | İndekslenmiş ve yüklü şirket belgelerini listeleme |
| `POST` | `/api/v1/upload-file` | Yeni PDF, DOCX veya TXT belgesi yükleme ve indeksleme |
| `DELETE` | `/api/v1/documents/{filename}` | Belgeyi diskten ve vektör veritabanından kalıcı silme |
| `POST` | `/api/v1/query` | Toplu (Batch) soru-cevap ve kaynak alıntıları |
| `POST` | `/api/v1/query-stream` | Canlı akış (NDJSON streaming) ile anlık yanıt alma |
| `GET` | `/api/v1/database/status` | Veritabanı bağlantı durumu, türü ve şema özeti |
| `POST` | `/api/v1/database/test-query` | Güvenli salt-okunur SQL çalıştırma |
| `POST` | `/api/v1/database/sync-table` | Veritabanı tablosunu ChromaDB vektör indeksine aktarma |

---

## 📖 Uç Nokta Detayları ve cURL Örnekleri

### 1. Sistem İstatistikleri (`GET /api/v1/stats`)
Sistem donanımını, kullanılan modelleri, belge ve parça sayılarını ve veritabanı durumunu döner.

```bash
curl -X GET "http://localhost:8000/api/v1/stats"
```

**Örnek Yanıt:**
```json
{
  "status": "success",
  "device": "CUDA (NVIDIA GPU)",
  "embedding_model": ".../models/bge-m3",
  "llm_model": ".../models/qwen2.5-1.5b",
  "total_chunks": 42,
  "total_documents": 3,
  "database": {
    "status": "connected",
    "dialect": "sqlite",
    "table_count": 3
  }
}
```

---

### 2. Belge Yükleme (`POST /api/v1/upload-file`)
Multipart/form-data ile gönderilen dosyayı `data/` klasörüne kaydeder, bağlamsal başlık enjekte ederek parçalar ve ChromaDB'ye ekler.

```bash
curl -X POST "http://localhost:8000/api/v1/upload-file" \
     -F "file=@NovaTech_Guvenlik_Politikasi.pdf"
```

---

### 3. Belge Silme (`DELETE /api/v1/documents/{filename}`)
Belirtilen dosyayı hem `data/` dizininden hem de ChromaDB koleksiyonundan tamamen siler.

```bash
curl -X DELETE "http://localhost:8000/api/v1/documents/NovaTech_Guvenlik_Politikasi.pdf"
```

---

### 4. Soru Sorma - Toplu Yanıt (`POST /api/v1/query`)
İndekslenmiş kurumsal veriler üzerinden yanıt ve referans kaynak alıntılarını döner.

```bash
curl -X POST "http://localhost:8000/api/v1/query" \
     -H "Content-Type: application/json" \
     -d '{
       "question": "Şirket bilgisayarlarında parola güncelleme periyodu nedir?"
     }'
```

**Örnek Yanıt:**
```json
{
  "status": "success",
  "answer": "Şirket bilgi güvenliği politikası gereğince parolalar en az 90 günde bir güncellenmelidir.",
  "sources": [
    {
      "source": "NovaTech_Guvenlik_Politikasi.pdf",
      "chunk_index": 2,
      "content": "[Belge: NovaTech Bilgi Güvenliği | KOD: SEC-04]\nMadde 3: Kullanıcı parolaları 90 günde bir...",
      "distance": 0.421,
      "reranker_score": 4.812
    }
  ]
}
```

---

### 5. Canlı Akış ile Soru Sorma (`POST /api/v1/query-stream`)
LangGraph iş akışıyla senkronize olarak çalışan **NDJSON (Newline Delimited JSON)** canlı akış protokolüdür.

```bash
curl -X POST "http://localhost:8000/api/v1/query-stream" \
     -H "Content-Type: application/json" \
     -d '{
       "question": "Donanım arızalarında destek sürecimiz nasıl işler?"
     }'
```

**Akış Boyunca Gelen Event Tipleri:**
1. `{"type": "status", "message": "🔍 İlgili şirket belgeleri taranıyor...", "node": "retrieve"}`
2. `{"type": "sources", "sources": [...]}`
3. `{"type": "status", "message": "✍️ Yanıt oluşturuluyor...", "node": "generate"}`
4. `{"type": "token", "token": "Donanım "}`
5. `{"type": "token", "token": "arızalarında "}`
6. `{"type": "status", "message": "🛡️ Kaynak uyumu ve doğruluk denetleniyor...", "node": "grade"}`
7. `{"type": "grade", "grade": "evet", "passed": true}`
8. `{"type": "done", "answer": "...", "sources": [...]}`
