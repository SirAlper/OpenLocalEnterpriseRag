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
|             (POST /api/v1/documents  |  POST /api/v1/query)             |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                        LangGraph Workflow Engine                        |
|                                                                         |
|   +-------------------+      Context       +------------------------+   |
|   |   Retrieve Node   | -----------------> |    Generation Node     |   |
|   +---------+---------+                    +-----------+------------+   |
|             |                                          |                |
+-------------|------------------------------------------|----------------+
              |                                          |
              v                                          v
+-----------------------------+            +------------------------------+
|     ChromaDB Vector Store   |            |      Hugging Face / PyTorch  |
|  (all-MiniLM-L6-v2 Embeds)  |            |   (Phi-3-mini / Llama-3 SLM) |
+-----------------------------+            +------------------------------+
```

---

## 🚀 Temel Özellikler

* **%100 Veri Gizliliği:** Harici sunuculara veya API'lere hiçbir istek iletilmez.
* **Hafif ve Hızlı Vektör Arama:** Kalıcı (Persistent) ChromaDB motoruyla milisaniyeler seviyesinde yerel semantik arama.
* **Ajan Karar Döngüsü (LangGraph):** Arama ve üretim safhalarını modüler düğümler halinde yöneten grafik tabanlı mimari.
* **Optimize Model Desteği:** Tüketici sınıfı veya kurumsal GPU'larda bfloat16/int4 formatlarında çalışabilen küçük dil modelleri (SLM).
* **Üretime Hazır API:** Otomatik Swagger/OpenAPI dokümantasyonuna sahip modern FastAPI altyapısı.

---

## 💻 Sistem & Donanım Gereksinimleri

| Bileşen | Minimum | Önerilen |
| :--- | :--- | :--- |
| **İşletim Sistemi** | Ubuntu 22.04 LTS / Windows 11 | Ubuntu 22.04 LTS |
| **Python** | 3.10+ | 3.11 |
| **Sistem Belleği (RAM)** | 16 GB DDR4/DDR5 | 32 GB RAM |
| **GPU / VRAM** | NVIDIA GPU (Min 6 GB VRAM) | NVIDIA RTX 3080/4080 / A4000 (12+ GB VRAM) |
| **CUDA Desteği** | CUDA 11.8+ | CUDA 12.1+ |

*(Not: CUDA destekli bir GPU bulunmadığında modeller CPU üzerinde çalıştırılabilir; ancak çıkarım süresi uzar.)*

---

## 📁 Dizin Yapısı

```text
local-enterprise-rag/
├── data/                  # Ham şirket belgelerinin tutulduğu klasör (PDF, DOCX, TXT)
├── vector_db/             # ChromaDB kalıcı vektör dizini
├── ui/
│   └── app.py             # Streamlit tabanlı modern kullanıcı ve yönetim arayüzü
├── src/
│   ├── __init__.py
│   ├── config.py          # Sistem, dosya yolları ve model yapılandırması
│   ├── document_loader.py # PDF/DOCX/TXT okuyucu ve artımlı metin parçalayıcı
│   ├── rag_engine.py      # Embedding, silme, istatistik ve kaynaklı arama motoru
│   ├── agent_graph.py     # LangGraph düğümleri ve yürütme mantığı
│   └── main.py            # FastAPI sunucusu, yönetim ve REST API uç noktaları
├── requirements.txt       # Proje bağımlılıkları listesi
├── .gitignore             # Vektör veri tabanını ve önbellekleri hariç tutma kuralları
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

Kurulumun doğru yapıldığını ve GPU'nun algılandığını doğrulamak için:
```bash
python -c "import torch; print('CUDA Aktif:', torch.cuda.is_available())"
```

### 4. Diğer Bağımlılıkları Yükleyin
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. İlk Çalıştırma ve Model İndirmeleri (Önemli Not)

Sistem ilk kez ayağa kaldırılırken yapılandırılan model Hugging Face Hub üzerinden yerel önbelleğinize indirilir. Bu tek seferlik bir işlemdir.

İndirme sırasında Hugging Face hız sınırlamalarına takılmamak ve indirmeyi hızlandırmak için:

```bash
# 1. Hızlı indirme motorunu yükleyin
pip install hf-transfer huggingface_hub

# 2. Hızlı indirmeyi aktif edin (Windows PowerShell)
$env:HF_HUB_ENABLE_HF_TRANSFER=1
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

---

## 🗺️ Gelecek Yol Haritası (Roadmap)

### 🧠 Gelişmiş RAG Teknikleri (Advanced Retrieval)
- [x] **Kaynak Gösterimi (Citation & Source Attribution):** Üretilen yanıtın hangi belgeden, sayfadan ve metin parçasından alındığını gösteren referans mekanizması.
- [ ] **Reranker (Yeniden Sıralayıcı):** ChromaDB'den dönen sonuçları `bge-reranker` gibi hafif bir modelle yeniden puanlayarak en alakalı bağlamı seçme.
- [ ] **Hibrit Arama (Hybrid Search):** Anlamsal vektör araması ile anahtar kelime aramasını (BM25) RRF (Reciprocal Rank Fusion) ile birleştirme.
- [ ] **Zengin Format & Tablo Desteği:** Excel (`.xlsx`), CSV ve tablolardan oluşan kurumsal veriler için yapısal veri ayrıştırma (parsing/chunking).

### 🤖 LangGraph & Ajan Mimarisi (Agentic RAG)
- [ ] **Sohbet Geçmişi & Bellek (Multi-Turn Chat History):** LangGraph Memory / Checkpointer entegrasyonu ile oturum bazlı bağlam takibi.
- [ ] **Akıllı Niyet Yönlendirici (Intent Router):** Genel sohbet (chitchat) ile belge sorgusunu ayırt edip gereksiz vektör aramalarını engelleyen yönlendirme düğümü.
- [ ] **Halüsinasyon Denetleyici (Hallucination Grader / Self-Correction):** Üretilen cevabın verilen bağlama sadakatini denetleyen ve gerekirse aramayı revize eden kontrol döngüsü.

### ⚡ Performans ve Hız Optimizasyonu
- [ ] **Akışkan Yanıt (Streaming SSE / WebSocket):** Yanıtların kelime kelime ekrana dökülmesini sağlayan asenkron akış mimarisi.
- [ ] **Ollama / GGUF (llama.cpp) & vLLM Entegrasyonu:** 4-bit kuantize edilmiş yerel modeller ile minimum VRAM/RAM tüketimi ve yüksek çıkarım hızı.
- [x] **Artımlı (Incremental) İndeksleme:** Yalnızca yeni yüklenen belgeleri işleyen ve arka planda çalışan optimize yükleme hattı.

### 🏢 Kurumsal Güvenlik & İzlenebilirlik (Enterprise Readiness)
- [ ] **Kullanıcı Yetkilendirme & RBAC:** Kullanıcı/departman rollerine göre belge ve koleksiyon erişim kontrolü.
- [ ] **Gözlemlenebilirlik (Observability / Tracing):** Yanıt gecikmesi, token ve erişim metriklerini takip etmek için Langfuse veya Arize Phoenix entegrasyonu.
- [ ] **Konteynerizasyon:** GPU destekli Docker ve Docker-Compose ile tek komutla kurulum altyapısı.

---

## 📄 Lisans

Bu proje [MIT Lisansı](LICENSE) ile lisanslanmıştır. Kurumsal ve ticari amaçlarla serbestçe kullanılabilir ve özelleştirilebilir.