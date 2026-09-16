# 🏗️ Sistem Mimarisi ve Çalışma Prensipleri

`OpenLocalEnterpriseRag`, verilerin harici bulut sağlayıcılarına (OpenAI, Anthropic vb.) gönderilmesini engelleyerek, tamamen yerel donanımda çalışan **iki aşamalı arama (Two-Stage Retrieval)** ve **durum tabanlı ajan (Agentic AI)** prensiplerine dayanır.

---

## 📐 Genel Mimari Şeması

```text
+-------------------------------------------------------------------------+
|                              FastAPI Gateway                            |
|        (POST /api/v1/documents  |  POST /api/v1/query)                  |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                        LangGraph Workflow Engine                        |
|                                                                         |
|   +-------------------+                +------------------------+       |
|   |   Retrieve Node   | -------------> |    Generation Node     |       |
|   +---------+---------+                +-----------+------------+       |
|             |                                      |                    |
|             |                                      v                    |
|             |                          +------------------------+       |
|             |                          |   Hallucination Grader |       |
|             |                          +-----------+------------+       |
|             |                                      |                    |
|             |              +-----------------------+------------------+ |
|             |              | [Doğrulandı]          | [Şüpheli & Retry]| |
|             |              v                       v                  | |
|             |            [END]             +-------------------+      | |
|             |                              |    Refine Node    |      | |
|             |                              | (Self-Correction) |      | |
|             |                              +---------+---------+      | |
|             |                                        |                | |
|             |                                        v                | |
|             |                                      [END]              | |
|             |              | [Limit Aşıldı]                           | |
|             |              +------------------------------------------+ |
|             |                                      |                    |
|             |                                      v                    |
|             |                              +---------------+            |
|             |                              | Fallback Node |            |
|             |                              +-------+-------+            |
|             |                                      |                    |
|             |                                      v                    |
|             |                                    [END]                  |
+-------------|-----------------------------------------------------------+
              |
              v
+-----------------------------+     +-------------------------------+
|     ChromaDB Vector Store   |     |    CrossEncoder Reranker      |
|    (BAAI/bge-m3 Embeds)     |     |  (BAAI/bge-reranker-v2-m3)   |
+-----------------------------+     +-------------------------------+
```

---

## 🔍 İki Aşamalı Arama & Yeniden Sıralama (Two-Stage Retrieval)

Geleneksel RAG sistemlerinde yalnızca vektör benzerliği (Cosine Similarity) kullanılır; bu durum semantik olarak yakın görünen ancak soruya doğrudan cevap vermeyen parçaların seçilmesine yol açabilir. Projemiz bu sorunu iki aşamalı bir yaklaşımla çözer:

### 1. Aşama: Hızlı Vektör Arama (Bi-Encoder / BAAI/bge-m3)
* **Model:** `BAAI/bge-m3` (1024 boyutlu yoğun vektörler).
* **İşlem:** Kullanıcının sorusu vektörleştirilir ve ChromaDB üzerinde milisaniyeler içinde taranarak geniş bir aday havuzu (`n_results=10`) çekilir.
* **Mesafe Eşiği (Distance Threshold):** Çok uzak veya alakasız parçalar (`max_distance=1.35`) bu aşamada doğrudan elenir.

### 2. Aşama: Çapraz Kodlayıcı ile Yeniden Sıralama (Cross-Encoder / BAAI/bge-reranker-v2-m3)
* **Model:** `BAAI/bge-reranker-v2-m3`
* **İşlem:** Kalan aday parçalar, soru ile ikili çiftler halinde (`[Soru, Belge Parçası]`) Cross-Encoder modeline verilir.
* **Sonuç:** Model, sorunun belge tarafından gerçekten yanıtlanıp yanıtlanmadığını tam dikkat mekanizmasıyla (Full-Attention) puanlar. En yüksek puanlı `RERANKER_TOP_N = 3` parça seçilerek LLM'e bağlam olarak iletilir.

---

## 📑 Bağlamsal Parçalama (Contextual Chunking)

Standart metin parçalayıcılar (text splitters), metni belirli karakter veya token sınırlarında keser. Bu durum, belgenin başlığı ve kodundan kopmuş metin parçalarının semantik anlamını yitirmesine neden olur.

`src/rag/document_loader.py` modülü **Bağlamsal Parçalama** uygular:
1. Belgenin ilk 5 satırı taranarak belge adı ve doküman kodu çıkarılır:
   - Örnek: `[Belge: NovaTech Bilgi Güvenliği Esasları | KOD: SEC-POL-04]`
2. Bu başlık, o belgeden türetilen **her bir parçanın en başına otomatik olarak enjekte edilir**:
   ```text
   [Belge: NovaTech Bilgi Güvenliği Esasları | KOD: SEC-POL-04]
   Madde 4.1: Şirket bilgisayarlarında USB bellek kullanımı bilgi işlem onayına tabidir...
   ```
3. Böylece embedding modeli arama yaparken parçanın hangi belge ve kural setine ait olduğunu tam olarak anlar.

---

## 🤖 LangGraph Durum Grafı ve Öz-Düzeltmeli Denetim (Self-RAG & Refinement)

İş akışı tek yönlü doğrusal bir boru hattı değil, geri beslemeli ve durum kontrollü bir LangGraph grafiğidir (`src/agent/agent_graph.py`):

1. **`retrieve` Düğümü:**
   - ChromaDB + Reranker motorunu çalıştırır.
   - Eğer eşleşen hiçbir kurumsal belge bulunamazsa doğrudan *"Bu bilgi şirket belgelerinde bulunmamaktadır"* yanıtına yönlendirir.
2. **`generate` Düğümü:**
   - `Qwen2.5-1.5B-Instruct` modeli devreye girerek belgelere sadık kalarak yanıt üretir.
3. **`grade` Düğümü (Hallucination Grader):**
   - Üretilen yanıt ile bağlamı karşılaştırır. Paraphrase (farklı sözcüklerle ifade etme) veya özetleme halüsinasyon sayılmaz; doğrudan belgede olmayan çelişkili veya uydurma iddialar tespit edilir.
4. **Koşullu Karar (`decide_hallucinate`):**
   - **Doğrulandı (Evet):** Akış başarıyla sonlandırılır (`END`), kaynaklar ve doğrulanmış cevap kullanıcıya sunulur.
   - **Şüpheli / Doğrulanamadı (Hayır):**
     - Eğer yanıt daha önce düzeltilmediyse (`retry_count < 1`), doğrudan `fallback`'e düşmek yerine **`refine`** düğümüne yönlendirilir.
     - Deneme limiti aşıldıysa son çare olarak güvenli `fallback` düğümü devreye girer.
5. **`refine` Düğümü (Self-Correction & Budama):**
   - Uzun yanıtlarda doğru bilgilerin gereksiz yere silinmesini önler.
   - Taslak yanıttaki belgesiz/spekülatif cümleleri çıkarıp budar, yalnızca bağlam tarafından kesin doğrulanan bilgileri koruyarak yanıtı profesyonelce yeniden yapılandırır.
6. **Kullanıcı Deneyimi:**
   - Token bazlı parçalı akış yerine, model arka planda düşünüp doğrulama yaparken arayüzde *"💭 Düşünülüyor ve belgeler inceleniyor..."* durumu gösterilir. İş akışı tamamlandığında nihai ve doğrulanmış yanıt eksiksiz bir mesaj olarak ekrana basılır.

