# 🏢 OpenLocalEnterpriseRag

[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?logo=pytorch&logoColor=white)](https://pytorch.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Privacy Protected](https://img.shields.io/badge/Privacy-100%25%20On--Premise-brightgreen.svg)](#)

> **Kurumsal ölçekte hassas şirket verilerinin üçüncü taraf bulut sağlayıcılarına (OpenAI, Anthropic vb.) aktarılmasını engelleyen; tamamen yerel donanım (On-Premise / Özel Sunucu) üzerinde çalışan açık kaynaklı RAG ve Ajan (Agentic AI) platformu.**

---

## ✨ Temel Yetenekler

* 🔒 **%100 Yerel ve Çevrimdışı (Air-Gapped):** Tüm embedding, yeniden sıralama (reranking) ve LLM çıkarımları yerel GPU/CPU'da gerçekleşir. Sıfır veri sızıntısı ve sıfır API maliyeti.
* 🎯 **İki Aşamalı Arama (Two-Stage Retrieval):** `BAAI/bge-m3` vektör araması ve `BAAI/bge-reranker-v2-m3` Cross-Encoder ile en alakalı şirket bağlamını milisaniyeler içinde tespit etme.
* 🛡️ **LangGraph Öz-Düzeltmeli Halüsinasyon Kalkanı (Self-Correction & Refinement):** Üretilen yanıtın şirket belgeleriyle sadakatini denetleyen, uzun yanıtlarda belgesiz kısımları budayarak düzelten ve gerektiğinde güvenli `fallback` sağlayan ajan grafı.
* 🗄️ **Evrensel Veritabanı Bağlayıcı (Database-Agnostic):** SQLAlchemy tabanlı konnektör ile **PostgreSQL, MSSQL, MySQL, Oracle veya SQLite** üzerinden canlı Text-to-SQL ve tablo vektörleştirme.
* ⚡ **Düşünme Durumu & Temiz İletişim (Thinking Indicator UX):** Model düşünürken ve belgeleri incelerken kullanıcıyı bilgilendiren, karmaşık token parçalanması yerine nihai onaylı yanıtı tek seferde sunan kararlı arayüz mimarisi.
* 🖥️ **Modern Kullanıcı Arayüzü & REST API:** FastAPI Swagger dokümantasyonu ve Streamlit tabanlı modern yönetim paneli.


---

## 📚 Dokümantasyon Merkezi (Docs Hub)

Detaylı teknik konular ve kılavuzlar için özel dokümantasyon sayfalarımızı inceleyebilirsiniz:

| Dokümantasyon Kılavuzu | Açıklama |
| :--- | :--- |
| 🏗️ [**Sistem Mimarisi**](docs/architecture.md) | LangGraph graf yapısı, çift aşamalı reranker ve contextual chunking mimarisi |
| 📦 [**Kurulum ve Donanım Kılavuzu**](docs/installation.md) | Donanım matrisi (VRAM/RAM), CUDA & PyTorch kurulumu ve çevrimdışı modeller |
| 🗄️ [**Veritabanı Entegrasyonu**](docs/database_connectors.md) | SQLAlchemy şablonları, Text-to-SQL aracı, güvenlik korumaları ve ETL aktarımı |
| 🔌 [**REST API Dokümantasyonu**](docs/api_reference.md) | Tüm FastAPI uç noktaları, NDJSON canlı akış protokolü ve cURL örnekleri |
| 🗺️ [**Gelecek Yol Haritası**](docs/roadmap.md) | Hibrit arama (BM25), GraphRAG, çok turlu sohbet hafızası ve vLLM entegrasyonu |

---

## ⚡ 3 Adımda Hızlı Başlangıç

### 1. Depoyu Klonlayın ve Bağımlılıkları Yükleyin
```bash
git clone https://github.com/kullaniciadi/OpenLocalEnterpriseRag.git
cd OpenLocalEnterpriseRag

# Sanal ortam
python -m venv .venv
.\.venv\Scripts\activate  # Linux/macOS: source .venv/bin/activate

# Donanımınıza uygun PyTorch (CUDA 12.1 için) ve paketler
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
```

### 2. Modelleri Yerel Dizine Sabitleyin (Tek Seferlik)
Modelleri doğrudan `./models/` klasörüne sabitlemek ve temp şişmesini önlemek için:
```bash
python download_model.py
```

### 3. Servisleri Başlatın
Ayrı terminal pencerelerinde:

```bash
# 1. Terminal - Backend API Sunucusu (FastAPI):
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
# Swagger API: http://localhost:8000/docs

# 2. Terminal - Web Yönetim Paneli (Streamlit):
streamlit run ui/app.py
# Web Paneli: http://localhost:8501
```

---

## 📁 Dizin Mimarisi

```text
OpenLocalEnterpriseRag/
├── data/                  # Şirket belgeleri (PDF, DOCX, TXT) ve örnek SQLite veritabanı
├── models/                # Yerel model ağırlıkları (Qwen2.5-1.5B, BGE-M3, BGE-Reranker)
├── vector_db/             # ChromaDB kalıcı vektör koleksiyonu
├── ui/
│   └── app.py             # Streamlit tabanlı kullanıcı ve yönetim arayüzü
├── src/
│   ├── core/              # Çekirdek yapılandırma, dosya yolları ve ortam değişkenleri
│   ├── rag/               # Doküman yükleyici ve ChromaDB/Reranker arama motoru
│   ├── agent/             # LangGraph grafı, LLM yükleyici, promptlar ve SQL/hesap araçları
│   ├── connectors/        # SQLAlchemy evrensel veritabanı bağlayıcı ve ETL aktarıcısı
│   ├── api/               # FastAPI REST API sunucusu ve otomatik indeksleme
│   └── main.py            # Geriye dönük uyumlu giriş noktası (uvicorn src.main:app)
├── docs/                  # [Detaylı Dokümantasyon](docs/)
├── download_model.py      # Modelleri doğrudan models/ içine indiren betik
└── requirements.txt       # Proje bağımlılıkları listesi
```

---

## 📄 Lisans

Bu proje [MIT Lisansı](LICENSE) ile lisanslanmıştır. Kurumsal ve ticari amaçlarla serbestçe kullanılabilir, değiştirilebilir ve dağıtılabilir.