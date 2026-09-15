# 🗄️ Kurumsal Veritabanı Entegrasyonu (SQLAlchemy)

`OpenLocalEnterpriseRag`, belirli bir şirketin veya tek bir veritabanı sağlayıcısının mimarisine bağımlı kalmadan; **PostgreSQL, MSSQL, MySQL, Oracle veya SQLite** gibi tüm ilişkisel veritabanlarına evrensel olarak bağlanabilen **SQLAlchemy tabanlı modüler bir konnektör katmanı** (`src/connectors/`) içerir.

---

## 🎯 Yetenekler ve Kullanım Modelleri

Sistem iki farklı veritabanı entegrasyon modelini destekler:

1. **Canlı SQL Sorgulama (Text-to-SQL Tool):**
   - Sayısal, tablosal ve anlık değişen veriler için (satışlar, stoklar, siparişler).
   - Dil modeli veritabanını dinamik olarak inceler ve salt-okunur `SELECT` sorguları üreterek anında yanıt döner.
2. **Tablo Vektörleştirme (Table-to-Vector ETL):**
   - Veritabanındaki metin kolonlarını (destek kayıtları, CRM görüşme notları, ürün açıklamaları) bağlamsal başlıklarla parçalayarak ChromaDB vektör motoruna indeksler.

---

## ⚙️ Yapılandırma (`.env` veya Ortam Değişkenleri)

Sisteme veritabanı bağlamak için tek bir ortam değişkeni (`DATABASE_URL`) tanımlamak yeterlidir:

```env
# 1. PostgreSQL
DATABASE_URL=postgresql+psycopg2://kullanici:sifre@localhost:5432/sirket_db

# 2. Microsoft SQL Server (MSSQL)
DATABASE_URL=mssql+pyodbc://kullanici:sifre@host:1433/sirket_db?driver=ODBC+Driver+17+for+SQL+Server

# 3. MySQL
DATABASE_URL=mysql+pymysql://kullanici:sifre@localhost:3306/sirket_db

# 4. Oracle
DATABASE_URL=oracle+cx_oracle://kullanici:sifre@localhost:1521/?service_name=sirket_db

# 5. Yerel Test / SQLite (Varsayılan):
DATABASE_URL=sqlite:///./data/sample_enterprise.db
```

### Güvenlik ve Tablo Filtresi (Whitelisting):
Şirketlerin maaş, şifre ve kimlik bilgileri içeren hassas tabloları gizleyebilmesi için opsiyonel filtre sunulur:

```env
# Yalnızca bu tablolara erişime izin ver:
DB_ALLOWED_TABLES=urunler,satislar,destek_talepleri

# Tek sorguda dönebilecek azami satır sayısı (varsayılan: 50):
DB_MAX_ROWS=50
```

---

## 🔒 Güvenlik ve Koruma Kalkanı (Strict Read-Only Guard)

Yapay zekanın veritabanını bozmasını veya yetkisiz işlemler yapmasını engellemek için kod seviyesinde çok katmanlı güvenlik uygulanır (`src/connectors/db_connector.py`):

* **Yalnızca `SELECT` İzni:** Sorgular `SELECT` veya `WITH ... SELECT` ile başlamak zorundadır.
* **Zararlı Komut Engeli:** `DROP`, `INSERT`, `UPDATE`, `DELETE`, `ALTER`, `TRUNCATE`, `EXEC`, `CREATE`, `GRANT`, `REVOKE` kelimelerini içeren sorgular anında reddedilir.
* **Bellek Koruma:** `max_rows` sınırlaması ile veritabanının kilitlenmesi veya belleğin şişmesi engellenir.

---

## 🔄 Tablo Vektörleştirme (ETL Senkronizasyonu)

Veritabanındaki bir tabloyu vektörleştirip ChromaDB'ye eklemek için:

### Arayüz Üzerinden (Streamlit):
1. Sol paneldeki **"🗄️ Veritabanı"** sekmesini açın.
2. Açılır menüden indekslemek istediğiniz tabloyu (örn: `destek_talepleri`) seçin.
3. **"🔄 Tabloyu Vektörleştir"** butonuna tıklayın.

### REST API Üzerinden:
```bash
curl -X POST "http://localhost:8000/api/v1/database/sync-table" \
     -H "Content-Type: application/json" \
     -d '{
       "table_name": "destek_talepleri"
     }'
```

---

## 🧪 Tak-Çalıştır Örnek Veritabanı (`sample_enterprise.db`)

Projeyi yeni klonlayan bir geliştiricinin harici bir veritabanı sunucusu kurmasına gerek kalmaması için, sistem ilk açılışta otomatik olarak `data/sample_enterprise.db` dosyasını oluşturur.

İçerisinde hazır mock kurumsal veriler bulunur:
- **`urunler`:** Ürün SKU, kategori, fiyat ve stok miktarları.
- **`satislar`:** Sipariş no, müşteri adı, bölge, tutar ve tarihler.
- **`destek_talepleri`:** Teknik destek konuları, müşteri talepleri ve çözüm adımları.
