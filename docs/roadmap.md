# 🗺️ Gelecek Yol Haritası (Roadmap)

`OpenLocalEnterpriseRag` projesinin açık kaynaklı vizyonunu dünya standartlarında bir kurumsal yapay zeka altyapısına taşımak için planlanan geliştirme aşamaları aşağıda kategorize edilmiştir.

---

## 🔍 1. İleri Düzey Arama & Zengin Veri Desteği (Advanced Retrieval)

- [ ] **Hibrit Arama (Hybrid Search / BM25 + Vektör):**
  - Anlamsal vektör araması ile anahtar kelime/kod aramasını (BM25) *Reciprocal Rank Fusion (RRF)* ile birleştirerek ürün kodları veya teknik terimlerde %100 isabet sağlama.
- [ ] **Zengin Format & Tablo Ayrıştırma:**
  - Excel (`.xlsx`), CSV ve karmaşık PDF tablolarından oluşan kurumsal veriler için yapısal veri ayrıştırma (unstructured table parsing & chunking).
- [ ] **Hiyerarşik & Parent-Child Parçalama:**
  - Küçük metin parçalarıyla hassas arama yapıp LLM üretimine üst başlık ve geniş bağlamı sunan iki katmanlı indeksleme.
- [ ] **Graf Tabanlı RAG (GraphRAG):**
  - Kurumsal belgeler arasındaki varlıkları (Entity) ve ilişkileri bilgi grafiğine (Knowledge Graph) dönüştürerek derin nedensellik ve çapraz analiz sorguları yapabilme.

---

## 🤖 2. Yeni Nesil Ajan Mimarisi (Next-Gen Agentic RAG)

- [ ] **Çok Turlu Sohbet Belleği (Multi-Turn Chat with Checkpointer):**
  - LangGraph Memory / SqliteSaver entegrasyonu ile kullanıcı oturumlarını ve önceki konuşma bağlamını hatırlama.
- [ ] **Dinamik Sorgu Yeniden Yazma (Query Rewriter & Expansion):**
  - Kullanıcının eksik veya muğlak sorularını vektör aramasına en uygun formata çeviren akıllı ajan düğümü.
- [x] **İlişkisel Veritabanı ve Text-to-SQL Entegrasyonu (SQL Database Connector & Tools):**
  - SQLAlchemy tabanlı evrensel konnektör (`src/connectors/db_connector.py`) ile PostgreSQL, MSSQL, MySQL, Oracle ve SQLite desteği tamamlandı.
  - Sıkı salt-okunur (strict read-only) güvenlik filtreleri, otomatik `LIMIT` ve tablo beyaz listesi (`DB_ALLOWED_TABLES`) eklendi.
  - Tablo kayıtlarını ChromaDB formatına çeviren ETL motoru (`DatabaseTableLoader`) ve ajan araçları (`sql_db_query`, `sql_db_schema`) entegre edildi.
- [ ] **Yönlendirici & Çoklu Ajan Takımları (Router & Multi-Agent Teams):**
  - Soruları şirket dokümanı, ilişkisel veritabanı sorgusu veya hesaplama araçları arasında dinamik paylaştıran süpervizör (supervisor) ajan mimarisi.
- [ ] **Kullanıcı Geri Bildirim Döngüsü (Feedback Loop):**
  - Web arayüzü üzerinden yanıtları beğenme/beğenmeme (Thumbs up/down) metriklerini toplayarak retrieval doğruluğunu sürekli izleme.

---

## ⚡ 3. Çıkarım Motoru & Performans Hızlandırma (Serving Optimization)

- [ ] **Optimize Çıkarım Motoru Entegrasyonu (vLLM / llama.cpp):**
  - Sürekli batching (continuous batching) ve PagedAttention ile çoklu eşzamanlı isteklerde çıkarım hızını katlayarak artırma.
- [ ] **Semantik Önbellekleme (Semantic Caching):**
  - Daha önce sorulmuş benzer kurumsal soruları vektör benzerliğiyle önbelleğe alıp (Redis / GPTCache) sıfır GPU maliyetiyle anında yanıtlama.
- [ ] **Spekülatif Kod Çözme (Speculative Decoding):**
  - Küçük bir taslak model (draft model) kullanarak yerel LLM üretim hızını iki katına çıkarma.

---

## 🏢 4. Kurumsal Güvenlik, Uyumluluk & DevOps (Enterprise Readiness)

- [ ] **Rol Tabanlı Erişim Kontrolü (RBAC):**
  - Kullanıcı ve departman (İK, Hukuk, Finans, Mühendislik) rollerine göre ChromaDB koleksiyon ve doküman seviyesinde yetkilendirme.
- [ ] **Gözlemlenebilirlik & İzleme (Observability & Tracing):**
  - Yanıt gecikmesi, token tüketimi ve arama isabetini analiz etmek için Langfuse, Arize Phoenix veya OpenTelemetry entegrasyonu.
- [ ] **Tek Komutla Konteynerizasyon (Docker & NVIDIA Container Toolkit):**
  - GPU geçişli Dockerfile ve Docker-Compose dosyaları ile sıfır konfigürasyonlu sunucu kurulumu.
- [ ] **Kurumsal SSO & LDAP Entegrasyonu:**
  - Active Directory, Keycloak ve Okta ile tek noktadan güvenli kurumsal oturum açma altyapısı.
