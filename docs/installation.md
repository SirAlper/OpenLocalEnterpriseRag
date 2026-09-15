# 📦 Kurulum ve Donanım Kılavuzu

Bu kılavuz, `OpenLocalEnterpriseRag` sisteminin yerel iş istasyonlarında veya kurumsal sunucularda donanım hızlandırmalı olarak nasıl kurulacağını adım adım açıklar.

---

## 💻 Sistem ve Donanım Gereksinimleri

Sistem, bge-m3 embedding, bge-reranker ve Qwen2.5-1.5B modelini aynı anda optimize şekilde çalıştıracak biçimde tasarlanmıştır:

| Bileşen | Minimum | Önerilen Kurumsal |
| :--- | :--- | :--- |
| **İşletim Sistemi** | Ubuntu 22.04 LTS / Windows 11 | Ubuntu 22.04 LTS / Windows 11 / RHEL 9 |
| **Python** | 3.10+ | 3.11 veya 3.12 |
| **Sistem RAM** | 8 GB DDR4 | 16 GB+ RAM |
| **GPU / VRAM** | NVIDIA GPU (**Min 4-6 GB VRAM**) | NVIDIA RTX 3060 / 4060 / A4000+ (8+ GB VRAM) |
| **CUDA Sürümü** | CUDA 11.8+ | CUDA 12.1+ |

> **Bellek Dağılım Notu:**  
> - `bge-m3` Embedding: ~1.1 GB (CPU üzerinde çalıştırılarak VRAM korunur)  
> - `bge-reranker-v2-m3`: ~1.1 GB (CPU üzerinde çalıştırılır)  
> - `Qwen2.5-1.5B-Instruct` LLM: ~2.8 GB (BF16 formatında doğrudan GPU VRAM'e alınır)  
> - Toplam VRAM Tüketimi: **Sadece ~3 GB!** (NVIDIA kartı bulunmadığında tüm sistem CPU üzerinde de çalıştırılabilir).

---

## 🛠️ Adım Adım Kurulum

### 1. Depoyu Klonlayın
```bash
git clone https://github.com/kullaniciadi/local-enterprise-rag.git
cd local-enterprise-rag
```

### 2. Sanal Ortamı Oluşturun ve Aktifleştirin
```bash
# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate

# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\activate
```

### 3. PyTorch'u Donanımınıza Uygun CUDA Sürümüyle Kurun

> **Önemli:** Modellerin GPU hızlandırmasıyla çalışabilmesi için PyTorch'u doğrudan resmi CUDA indeksi üzerinden kurmalısınız.

* **NVIDIA GPU (CUDA 12.1 - Önerilen):**
  ```bash
  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
  ```

* **NVIDIA GPU (CUDA 11.8):**
  ```bash
  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
  ```

* **Yalnızca CPU (Test ve Geliştirme):**
  ```bash
  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
  ```

### 4. Bağımlılıkları Yükleyin
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 📥 Modelleri Yerel Dizine Sabitleme (`download_model.py`)

Sistem çalışırken modellerin internetten indirilip `~/.cache` veya `Temp` dizinlerini şişirmesini önlemek için modeller doğrudan proje altındaki `./models/` klasörüne sabitlenir.

Tek seferlik çalıştırmanız yeterlidir:
```bash
python download_model.py
```

Bu komut şu modelleri indirir:
1. `models/bge-m3`: Çok dilli semantik vektör modeli (~1.1 GB)
2. `models/bge-reranker-v2-m3`: Çapraz kodlayıcı yeniden sıralayıcı (~1.1 GB)
3. `models/qwen2.5-1.5b`: Qwen 2.5 1.5B Türkçe uyumlu küçük dil modeli (~2.8 GB)

İndirme tamamlandığında sistem **tamamen çevrimdışı (offline)** modda çalışmaya hazırdır.

---

## 🚀 Servisleri Başlatma

### Backend (FastAPI API Sunucusu):
```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```
* **Swagger API Dokümantasyonu:** `http://localhost:8000/docs`

### Frontend (Streamlit Kullanıcı Paneli):
Ayrı bir terminal penceresinde:
```bash
streamlit run ui/app.py
```
* **Kullanıcı Arayüzü:** `http://localhost:8501`
