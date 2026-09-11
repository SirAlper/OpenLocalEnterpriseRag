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
├── data/                  # Ham şirket belgelerinin tutulduğu klasör
├── vector_db/             # ChromaDB kalıcı vektör dizini
├── src/
│   ├── __init__.py
│   ├── config.py          # Sistem, dosya yolları ve model yapılandırması
│   ├── rag_engine.py      # Embedding ve ChromaDB vektör motoru
│   ├── agent_graph.py     # LangGraph düğümleri ve yürütme mantığı
│   └── main.py            # FastAPI sunucusu ve REST API uç noktaları
├── requirements.txt       # Proje bağımlılıkları listesi
├── .gitignore             # Vektör veri tabanını ve önbellekleri hariç tutma kuralları
└── README.md              # Proje dokümantasyonu
```

---

## 📦 Kurulum ve Çalıştırma

### 1. Depoyu Klonlayın
```bash
git clone [https://github.com/kullaniciadi/local-enterprise-rag.git](https://github.com/kullaniciadi/local-enterprise-rag.git)
cd local-enterprise-rag
```

### 2. Sanal Ortamı Hazırlayın
```bash
# Linux / macOS
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Bağımlılıkları Yükleyin
```bash
pip install --upgrade pip
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
pip install -r requirements.txt
```

### 4. Servisi Başlatın
```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

Swagger API Arayüzü: `http://localhost:8000/docs`

---

## 🔌 API Kullanım Özeti

### Doküman Ekleme (`POST /api/v1/documents`)
Şirket içi yönetmelikleri, kılavuzları veya belgeleri vektör veritabanına indekslemek için kullanılır.

* **İstek Gövdesi:**
  * `texts`: İndekslenecek metin parçalarının listesi.
  * `ids`: Her bir belge parçası için benzersiz kimlik listesi.

### Yapay Zekaya Soru Sorma (`POST /api/v1/query`)
İndekslenen şirket verileri üzerinden yerel dil modeli ile çıkarım yapmak için kullanılır.

* **İstek Gövdesi:**
  * `question`: Kullanıcının doğal dilde sorduğu soru.
* **Yanıt Gövdesi:**
  * `status`: İstek durumu (`success`).
  * `answer`: Sadece sağlanan şirket bağlamına dayalı üretilen net cevap.

---

## 🗺️ Gelecek Yol Haritası (Roadmap)

- [ ] **Doküman Ayrıştırıcı (Parser):** PDF, DOCX ve XLSX formatları için otomatik metin parçalama (chunking) desteği.
- [ ] **Doğrulama (Self-Correction) Düğümü:** Model çıktısının bağlama sadık kalıp kalmadığını denetleyen LangGraph kontrol düğümü.
- [ ] **vLLM Desteği:** Yüksek eşzamanlı istekler için vLLM çıkarım motoru entegrasyonu.
- [ ] **Konteynerizasyon:** GPU destekli Docker ve Docker-Compose yapılandırması.

---

## 📄 Lisans

Bu proje [MIT Lisansı](LICENSE) ile lisanslanmıştır. Kurumsal ve ticari amaçlarla serbestçe kullanılabilir ve özelleştirilebilir.