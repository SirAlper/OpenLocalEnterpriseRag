# Enterprise Local RAG & Agent System

[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11-blue.svg)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?logo=pytorch&logoColor=white)](https://pytorch.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Privacy Protected](https://img.shields.io/badge/Privacy-100%25%20On--Premise-brightgreen.svg)](#)

Kurumsal ölçekte hassas şirket verilerinin üçüncü taraf bulut sağlayıcılarına (OpenAI, Anthropic vb.) aktarılmasını engelleyen; tamamen yerel donanım (On-Premise / Özel Sunucu) üzerinde çalışan, modüler ve yüksek performanslı **Yerel RAG (Retrieval-Augmented Generation)** ve **Agentic AI** altyapısı.

---

## 📌 Projenin Amacı ve Kurumsal Değeri

Pek çok kurumsal firma, veri sızıntısı riskleri, regülasyonlar (KVKK, GDPR) ve API maliyetleri nedeniyle bulut tabanlı yapay zeka modellerini kullanamamaktadır. Bu proje:
* **Sıfır Dış Ağ Bağımlılığı:** Veriler sunucunun dışına çıkmaz, tamamen yerel ağda çalışır.
* **Maliyet Tasarrufu:** Token veya istek başına bulut API ücretlerini ortadan kaldırır.
* **Agentic Karar Mekanizması:** LangGraph ile klasik aramanın ötesine geçerek akıllı akış kontrolü sunar.
* **Entegrasyon Kolaylığı:** RESTful API mimarisi sayesinde ERP, CRM veya şirket içi portallara doğrudan bağlanabilir.

---

## 🏗️ Mimari Şema

```text
+-------------------------------------------------------------------------+
|                              FastAPI Gateway                            |
|        (POST /api/v1/documents  |  POST /api/v1/query-stream)           |
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
|             |                        [is_grounded] / \ [hallucinated]   |
|             |                                     v   v                 |
|             |                                   [END] [Fallback Node]   |
|             |                                               |           |
|             |                                               v           |
|             |                                             [END]         |
+-------------|-----------------------------------------------------------+
              |
              v
+-----------------------------+     +-------------------------------+
|     ChromaDB Vector Store   |     |    CrossEncoder Reranker      |
|    (BAAI/bge-m3 Embeds)     |     |  (BAAI/bge-reranker-v2-m3)   |
+-----------------------------+     +-------------------------------+
```

---

## 🚀 Temel Özellikler ve Gelişmiş Yetenekler

* **%100 Yerel ve Sıfır Veri Bağımlılığı:** Harici bulut sağlayıcılarına (OpenAI vb.) hiçbir veri iletilmez. Tüm embedding, reranking ve LLM çıkarımı yerel donanımda gerçekleşir.
* **İki Aşamalı Arama & Yeniden Sıralama (Two-Stage Retrieval & Reranker):**
  * **Birinci Aşama:** BAAI/bge-m3 çok dilli embedding modeli ile ChromaDB üzerinde milisaniyeler seviyesinde vektör arama.
  * **Vektör Mesafe Eşiği (Distance Threshold):** Alakasız ve düşük benzerlikli doküman parçalarını filtreleyen skor kalkanı.
  * **İkinci Aşama:** BAAI/bge-reranker-v2-m3 CrossEncoder modeliyle aday parçaları soru-metin çifti olarak yeniden puanlayarak en alakalı bağlamı (`RERANKER_TOP_N`) seçme.
* **Bağlamsal & Artımlı İndeksleme (Contextual & Incremental Indexing):**
  * **Contextual Chunking:** Her metin parçacığının başına ait olduğu belge başlığı ve kodunu otomatik enjekte ederek semantik bağlam kaybını engelleme.
  * **Artımlı İndeksleme:** Sunucu başlarken `data/` klasöründeki yeni belgeleri otomatik algılayıp yalnızca eksik olanları indeksleme.
* **LangGraph Tabanlı Ajan Döngüsü (Agentic RAG):** Arama (`Retrieve`), üretim (`Generate`) ve doğrulama düğümlerini durum tabanlı graf mimarisiyle yönetme.
* **Halüsinasyon Denetimi ve Sadakat Kontrolü (Hallucination Grader / Self-RAG):** Üretilen yanıtın verilen şirket bağlamına sadakatini kontrol eden ve gerekirse güvenli geri dönüş (`fallback`) mekanizmasını tetikleyen karar yapısı.
* **Kaynak Gösterimi ve Doğrulanabilirlik (Citations & Attribution):** Yanıtın hangi belgeden, hangi parça indeksinden ve hangi benzerlik skoruyla alındığını şeffafça sunma.
* **Gerçek Zamanlı Canlı Akış (Streaming via NDJSON):** `TextIteratorStreamer` tabanlı token akışını LangGraph düğüm durumları (`status`), alıntılanan kaynaklar (`sources`) ve doğrulama sonucuyla (`grade`) senkronize iletme.
* **Donanım ve Bellek Optimizasyonları:**
  * **bfloat16 & 4-bit (NF4) Kuantizasyon:** RTX 3060 gibi tüketici kartlarında dahi ~5 GB VRAM ile tam Türkçe çıkarım.
  * **Sabit Yerel Dizin (`./models`):** Modelleri proje dizininde sabitleyerek sistem önbelleklerinin (`~/.cache`, `Temp`) şişmesini önleme.
  * **Genişletilmiş Çıkarım Penceresi:** 512 token üretim sınırı ve SDPA dikkat hızlandırması.
* **Kurumsal REST API:** FastAPI ile modüler uç noktalar, dosya yükleme/silme yönetimi ve otomatik OpenAPI/Swagger arayüzü.

---

## 💻 Sistem & Donanım Gereksinimleri

| Bileşen | Minimum | Önerilen |
| :--- | :--- | :--- |
| **İşletim Sistemi** | Ubuntu 22.04 LTS / Windows 11 | Ubuntu 22.04 LTS / Windows 11 |
| **Python** | 3.10+ | 3.11 / 3.12 |
| **Sistem Belleği (RAM)** | 8 GB DDR4 | 16 GB+ RAM |
| **GPU / VRAM** | NVIDIA GPU (**Min 4-6 GB VRAM**) | NVIDIA RTX 3060 / 4060+ (8+ GB VRAM) |
| **CUDA Desteği** | CUDA 11.8+ | CUDA 12.1+ |

*(Not: bge-m3 Embedding (~1.1 GB) + bge-reranker-v2-m3 (~1.1 GB) + Qwen2.5-1.5B LLM (~2.8 GB BF16) = toplam ~5 GB VRAM. GPU bulunmadığında CPU üzerinde de çalıştırılabilir.)*

---

## 📁 Dizin Yapısı

```text
local-enterprise-rag/
├── data/                  # Ham şirket belgelerinin tutulduğu klasör (PDF, DOCX, TXT)
├── models/                # Yerel model ağırlıklarının tutulduğu dizin (SLM & Embedding)
├── vector_db/             # ChromaDB kalıcı vektör dizini
├── ui/
│   └── app.py             # Streamlit tabanlı modern kullanıcı ve yönetim arayüzü
├── src/
│   ├── __init__.py
│   ├── config.py          # Sistem, dosya yolları ve model yapılandırması
│   ├── llm.py             # ChatHuggingFace model yükleyici ve pipeline
│   ├── prompts.py         # RAG ve halüsinasyon denetim promptları
│   ├── document_loader.py # PDF/DOCX/TXT okuyucu ve artımlı metin parçalayıcı
│   ├── rag_engine.py      # Embedding, ChromaDB, CrossEncoder reranker motoru
│   ├── nodes.py           # LangGraph düğüm fonksiyonları (retrieve, generate, grade)
│   ├── agent_graph.py     # LangGraph graf orkestratörü ve canlı akış (streaming)
│   ├── tools.py           # İsteğe bağlı harici araç tanımları
│   └── main.py            # FastAPI sunucusu, yönetim ve REST API uç noktaları
├── download_model.py      # Modelleri doğrudan models/ içine indiren betik
├── requirements.txt       # Proje bağımlılıkları listesi
├── .gitignore             # Vektör veri tabanını ve modelleri hariç tutma kuralları
└── README.md              # Proje dokümantasyonu
```

---

## 📦 Kurulum ve Çalıştırma

### 1. Depoyu Klonlayın
```bash
git clone https://github.com/kullaniciadi/local-enterprise-rag.git
cd local-enterprise-rag
```

### 2. Sanal Ortamı Hazırlayın
```bash
# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate

# Windows (PowerShell / CMD)
python -m venv .venv
.\.venv\Scripts\activate
```

### 3. Donanımınıza Uygun PyTorch Sürümünü Kurun

> **Önemli:** Modellerin GPU hızlandırmasıyla çalışabilmesi için PyTorch'u doğrudan sisteminizdeki CUDA sürümüne uygun resmi indeks ile kurmalısınız.

* **NVIDIA GPU (CUDA 12.1 - Önerilen):**
  ```bash
  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
  ```
* **NVIDIA GPU (CUDA 11.8):**
  ```bash
  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
  ```
* **Yalnızca CPU (Test ve Geliştirme İçin):**
  ```bash
  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
  ```

### 4. Diğer Bağımlılıkları Yükleyin
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Modelleri Yerel Dizine İndirin (Tek Seferlik)

Modelleri doğrudan `./models` klasörüne sabitlemek ve temp/cache birikimini önlemek için:

```bash
python download_model.py
```

### 6. Servisleri Başlatın

#### A. Backend API'yi Başlatın:
```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```
* Swagger API Arayüzü: `http://localhost:8000/docs`

#### B. Kullanıcı Arayüzünü (Streamlit) Başlatın:
Ayrı bir terminalde:
```bash
streamlit run ui/app.py
```
* Web Dashboard: `http://localhost:8501`

---

## 🔌 API Kullanım Özeti

### 1. Sistem & Veritabanı İstatistikleri (`GET /api/v1/stats`)
Sistem donanımını (CUDA/CPU), kullanılan modelleri ve indekslenmiş toplam parça sayılarını döner.

### 2. Belgeleri Listeleme (`GET /api/v1/documents`)
Sistemde yüklü olan tüm belgeleri, dosya boyutlarını ve her birinin kaç parçaya bölündüğünü listeler.

### 3. Belge Yükleme ve İndeksleme (`POST /api/v1/upload-file`)
Multipart/form-data ile yüklenen dosyayı kaydeder, parçalar ve ChromaDB'ye ekler.

```bash
curl -X POST "http://localhost:8000/api/v1/upload-file" \
     -F "file=@sirket_politikasi.pdf"
```

### 4. Belge Silme (`DELETE /api/v1/documents/{filename}`)
Belirtilen dosyayı hem `data/` dizininden hem de ChromaDB vektör veritabanından kalıcı olarak siler.

```bash
curl -X DELETE "http://localhost:8000/api/v1/documents/sirket_politikasi.pdf"
```

### 5. Yapay Zekaya Soru Sorma (`POST /api/v1/query`)
İndekslenen şirket verileri üzerinden yanıt ve referans alınan kaynak alıntılarını döner.

* **İstek Gövdesi:**
  * `question`: Kullanıcının doğal dilde sorduğu soru.
* **Yanıt Gövdesi:**
  * `status`: `success`
  * `answer`: Üretilen cevap metni.
  * `sources`: Referans alınan belge adı, parça indeksi ve alıntı metinleri listesi.

```bash
curl -X POST "http://localhost:8000/api/v1/query" \
     -H "Content-Type: application/json" \
     -d '{
       "question": "İzin talebimi ne zaman bildirmeliyim?"
     }'
```

### 6. Canlı Akış ile Soru Sorma (`POST /api/v1/query-stream`)
LangGraph iş akışıyla tam senkronize çalışan gerçek zamanlı canlı akış (NDJSON streaming) sağlar.
Akış süresince sırasıyla şu olaylar (events) iletilir:
1. `status`: Aktif LangGraph düğümünün durumu (`🔍 İlgili şirket belgeleri taranıyor...`, `✍️ Yanıt oluşturuluyor...`, `🛡️ Kaynak uyumu ve doğruluk denetleniyor...`)
2. `sources`: Vektör tabanından çekilen referans belge ve parça bilgileri.
3. `token`: Dil modelinin ürettiği canlı metin parçacıkları.
4. `grade` / `warning`: Halüsinasyon ve doğrulama denetiminin sonucu.
5. `done`: Akışın tamamlandığı bilgisi.

```bash
curl -X POST "http://localhost:8000/api/v1/query-stream" \
     -H "Content-Type: application/json" \
     -d '{
       "question": "TechCorp çalışma saatleri nedir?"
     }'
```

---

## 🗺️ Gelecek Yol Haritası (Roadmap)

### 🔍 1. İleri Düzey Arama & Zengin Veri Desteği (Advanced Retrieval & Multi-Modal)
- [ ] **Hibrit Arama (Hybrid Search / BM25 + Vektör):** Anlamsal vektör araması ile anahtar kelime/kod aramasını (BM25) Reciprocal Rank Fusion (RRF) ile birleştirerek arama isabetini maksimize etme.
- [ ] **Zengin Format & Tablo Ayrıştırma:** Excel (`.xlsx`), CSV ve karmaşık PDF tablolarından oluşan kurumsal veriler için yapısal veri ayrıştırma (unstructured table parsing & chunking).
- [ ] **Hiyerarşik & Parent-Child Parçalama:** Küçük metin parçalarıyla hassas arama yapıp LLM üretimine üst başlık ve geniş bağlamı sunan iki katmanlı indeksleme.
- [ ] **Graf Tabanlı RAG (GraphRAG):** Kurumsal belgeler arasındaki varlıkları (Entity) ve ilişkileri bilgi grafiğine (Knowledge Graph) dönüştürerek derin nedensellik sorguları yapabilme.

### 🤖 2. Yeni Nesil Ajan Mimarisi (Next-Gen Agentic RAG)
- [ ] **Çok Turlu Sohbet Belleği (Multi-Turn Chat with Checkpointer):** LangGraph Memory / SqliteSaver entegrasyonu ile kullanıcı oturumlarını ve önceki konuşma bağlamını hatırlama.
- [ ] **Dinamik Sorgu Yeniden Yazma (Query Rewriter & Expansion):** Kullanıcının eksik veya muğlak sorularını vektör aramasına en uygun formata çeviren akıllı ajan düğümü.
- [ ] **Yönlendirici & Çoklu Ajan Orkestrasyonu (Router & Multi-Agent Teams):** Soruları şirket dokümanı, ilişkisel veritabanı sorgusu (Text-to-SQL) veya yerel araçlara dinamik yönlendiren süpervizör ajan mimarisi.
- [ ] **Kullanıcı Geri Bildirim Döngüsü (Feedback Loop):** Web arayüzü üzerinden yanıtları beğenme/beğenmeme (Thumbs up/down) metriklerini toplayarak retrieval doğruluğunu sürekli izleme.

### ⚡ 3. Çıkarım Motoru & Performans Hızlandırma (Serving Optimization)
- [ ] **Optimize Çıkarım Motoru Entegrasyonu (vLLM / llama.cpp):** Sürekli batching (continuous batching) ve PagedAttention ile çoklu eşzamanlı isteklerde çıkarım hızını katlayarak artırma.
- [ ] **Semantik Önbellekleme (Semantic Caching):** Daha önce sorulmuş benzer kurumsal soruları vektör benzerliğiyle önbelleğe alıp (Redis / GPTCache) sıfır GPU maliyetiyle anında yanıtlama.
- [ ] **Spekülatif Kod Çözme (Speculative Decoding):** Küçük bir taslak model (draft model) kullanarak yerel LLM üretim hızını iki katına çıkarma.

### 🏢 4. Kurumsal Güvenlik, Uyumluluk & DevOps (Enterprise Readiness)
- [ ] **Rol Tabanlı Erişim Kontrolü (RBAC):** Kullanıcı ve departman (İK, Hukuk, Finans, Mühendislik) rollerine göre ChromaDB koleksiyon ve doküman seviyesinde yetkilendirme.
- [ ] **Gözlemlenebilirlik & İzleme (Observability & Tracing):** Yanıt gecikmesi, token tüketimi ve arama isabetini analiz etmek için Langfuse, Arize Phoenix veya OpenTelemetry entegrasyonu.
- [ ] **Tek Komutla Konteynerizasyon (Docker & NVIDIA Container Toolkit):** GPU geçişli Dockerfile ve Docker-Compose dosyaları ile sıfır konfigürasyonlu sunucu kurulumu.
- [ ] **Kurumsal SSO & LDAP Entegrasyonu:** Active Directory, Keycloak ve Okta ile tek noktadan güvenli kurumsal oturum açma altyapısı.

---

## 📄 Lisans

Bu proje [MIT Lisansı](LICENSE) ile lisanslanmıştır. Kurumsal ve ticari amaçlarla serbestçe kullanılabilir ve özelleştirilebilir.