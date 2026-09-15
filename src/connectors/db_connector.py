import re
import os
import sqlite3
from typing import Optional, Dict, Any, List
from src.core.config import DATABASE_URL, DB_ALLOWED_TABLES, DB_MAX_ROWS, SAMPLE_DB_PATH


class DatabaseConnector:
    """SQLAlchemy tabanlı evrensel, veritabanı-bağımsız ve güvenli veritabanı bağlayıcısı.

    PostgreSQL, MySQL, SQLite, MSSQL, Oracle gibi tüm ilişkisel veritabanlarını
    tek bir arayüz üzerinden yönetir. Salt-okunur (read-only) güvenlik korumalarına sahiptir.
    """

    def __init__(
        self,
        database_url: Optional[str] = None,
        allowed_tables: Optional[List[str]] = None,
        max_rows: int = DB_MAX_ROWS
    ):
        self.database_url = database_url if database_url is not None else DATABASE_URL
        self.allowed_tables = allowed_tables if allowed_tables is not None else DB_ALLOWED_TABLES
        self.max_rows = max_rows
        self.engine = None
        self.is_connected = False
        self._last_error = None

        if self.database_url:
            self._init_engine()

    def _init_engine(self):
        """SQLAlchemy motorunu başlatır."""
        try:
            from sqlalchemy import create_engine
            # SQLite için relative path uyumluluğu ve thread güvenliği
            connect_args = {}
            if self.database_url.startswith("sqlite"):
                connect_args = {"check_same_thread": False}

            self.engine = create_engine(
                self.database_url,
                pool_pre_ping=True,
                connect_args=connect_args
            )
            # Test bağlantısı
            with self.engine.connect() as conn:
                pass
            self.is_connected = True
            self._last_error = None
        except Exception as e:
            self.engine = None
            self.is_connected = False
            self._last_error = str(e)
            print(f"[DatabaseConnector] Bağlantı başlatılamadı: {e}")

    def test_connection(self) -> Dict[str, Any]:
        """Bağlantıyı test eder, veritabanı türünü ve mevcut tabloları döner."""
        if not self.database_url:
            return {
                "status": "not_configured",
                "message": "Veritabanı URL'si (DATABASE_URL) tanımlanmamış.",
                "dialect": None,
                "tables": []
            }

        if not self.is_connected or not self.engine:
            self._init_engine()

        if not self.is_connected:
            return {
                "status": "error",
                "message": f"Bağlantı hatası: {self._last_error}",
                "dialect": None,
                "tables": []
            }

        try:
            tables = self.get_tables()
            dialect_name = self.engine.dialect.name
            return {
                "status": "connected",
                "message": f"Başarıyla bağlandı ({dialect_name.upper()}).",
                "dialect": dialect_name,
                "tables": tables,
                "table_count": len(tables)
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Tablolar sorgulanırken hata: {e}",
                "dialect": self.engine.dialect.name if self.engine else None,
                "tables": []
            }

    def get_tables(self) -> List[str]:
        """Erişilebilir tablo adlarını döner (izinli tablolar filtresiyle)."""
        if not self.is_connected or not self.engine:
            return []

        from sqlalchemy import inspect
        inspector = inspect(self.engine)
        all_tables = inspector.get_table_names()

        # Sistem/dahili tabloları hariç tut
        ignored_tables = {"sqlite_sequence"}
        tables = [t for t in all_tables if t not in ignored_tables]

        if self.allowed_tables:
            tables = [t for t in tables if t in self.allowed_tables]

        return sorted(tables)

    def get_schema_summary(self) -> str:
        """LLM promptları için veritabanı şemasını (tablolar, kolonlar, tipler) metin olarak üretir."""
        if not self.is_connected or not self.engine:
            return "Veritabanı bağlantısı aktif değil."

        try:
            from sqlalchemy import inspect
            inspector = inspect(self.engine)
            tables = self.get_tables()

            if not tables:
                return "Erişilebilir tablo bulunamadı."

            schema_lines = [f"# VERİTABANI ŞEMASI (Tür: {self.engine.dialect.name.upper()})"]

            for table in tables:
                columns = inspector.get_columns(table)
                pk_constraint = inspector.get_pk_constraint(table)
                pks = set(pk_constraint.get("constrained_columns", []) if pk_constraint else [])

                col_strs = []
                for col in columns:
                    col_name = col["name"]
                    col_type = str(col["type"])
                    is_pk = " [PK]" if col_name in pks else ""
                    col_strs.append(f"{col_name} ({col_type}{is_pk})")

                schema_lines.append(f"Tablo: {table}")
                schema_lines.append(f"  Kolonlar: {', '.join(col_strs)}")

            return "\n".join(schema_lines)
        except Exception as e:
            return f"Şema çıkarılırken hata: {e}"

    def execute_query(self, query: str) -> Dict[str, Any]:
        """Salt-okunur güvenlik denetimlerinden geçirerek SQL sorgusunu çalıştırır.

        Güvenlik Kuralları:
        1. Sadece 'SELECT' veya 'WITH ... SELECT' sorgularına izin verilir.
        2. 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'TRUNCATE', 'EXEC' gibi yazma/silme işlemleri engellenir.
        3. Sonuç satırları en fazla max_rows ile sınırlandırılır.
        """
        if not self.is_connected or not self.engine:
            return {
                "status": "error",
                "message": "Veritabanı bağlantısı aktif değil.",
                "columns": [],
                "rows": []
            }

        clean_query = query.strip().rstrip(";").strip()

        # 1. Zararlı anahtar kelime denetimi (Strict Read-Only Guard)
        forbidden_pattern = r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|EXEC|EXECUTE|CREATE|GRANT|REVOKE|REPLACE)\b"
        if re.search(forbidden_pattern, clean_query, re.IGNORECASE):
            return {
                "status": "error",
                "message": "Güvenlik Engeli: Yalnızca salt-okunur (SELECT) sorgular çalıştırılabilir.",
                "columns": [],
                "rows": []
            }

        # 2. SELECT veya WITH ile başlama kontrolü
        if not re.match(r"^(SELECT|WITH)\b", clean_query, re.IGNORECASE):
            return {
                "status": "error",
                "message": "Geçersiz Sorgu: Sorgu 'SELECT' veya 'WITH' ile başlamalıdır.",
                "columns": [],
                "rows": []
            }

        try:
            from sqlalchemy import text
            with self.engine.connect() as conn:
                result = conn.execute(text(clean_query))
                columns = list(result.keys()) if result.returns_rows else []
                raw_rows = result.fetchmany(self.max_rows) if result.returns_rows else []

                # JSON serileştirilebilir formata dönüştür
                formatted_rows = []
                for row in raw_rows:
                    row_dict = {}
                    for col, val in zip(columns, row):
                        if val is None:
                            row_dict[col] = None
                        elif isinstance(val, (int, float, bool, str)):
                            row_dict[col] = val
                        else:
                            row_dict[col] = str(val)
                    formatted_rows.append(row_dict)

                return {
                    "status": "success",
                    "columns": columns,
                    "rows": formatted_rows,
                    "row_count": len(formatted_rows),
                    "query": clean_query
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Sorgu yürütülürken hata: {e}",
                "columns": [],
                "rows": []
            }


def create_sample_sqlite_db(db_path: Optional[str] = None) -> str:
    """Açık kaynaklı depoyu klonlayanların anında test edebilmesi için örnek kurumsal SQLite veri tabanı üretir."""
    target_path = db_path or SAMPLE_DB_PATH
    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    conn = sqlite3.connect(target_path)
    cursor = conn.cursor()

    # 1. Ürünler Tablosu
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS urunler (
        urun_id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT UNIQUE NOT NULL,
        urun_adi TEXT NOT NULL,
        kategori TEXT NOT NULL,
        birim_fiyat REAL NOT NULL,
        stok_adedi INTEGER NOT NULL
    );
    """)

    # 2. Satışlar Tablosu
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS satislar (
        satis_id INTEGER PRIMARY KEY AUTOINCREMENT,
        siparis_no TEXT NOT NULL,
        musteri_adi TEXT NOT NULL,
        urun_id INTEGER,
        adet INTEGER NOT NULL,
        toplam_tutar REAL NOT NULL,
        bolge TEXT NOT NULL,
        tarih TEXT NOT NULL,
        FOREIGN KEY (urun_id) REFERENCES urunler(urun_id)
    );
    """)

    # 3. Destek Talepleri Tablosu
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS destek_talepleri (
        talep_id INTEGER PRIMARY KEY AUTOINCREMENT,
        talep_kodu TEXT NOT NULL,
        musteri_adi TEXT NOT NULL,
        konu TEXT NOT NULL,
        detay TEXT NOT NULL,
        cozum TEXT NOT NULL,
        durum TEXT NOT NULL
    );
    """)

    # Örnek veri kontrolü
    cursor.execute("SELECT COUNT(*) FROM urunler;")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("""
        INSERT INTO urunler (sku, urun_adi, kategori, birim_fiyat, stok_adedi) VALUES (?, ?, ?, ?, ?);
        """, [
            ("NT-SRV-01", "NovaTech Enterprise Sunucu X1", "Donanım", 85000.0, 14),
            ("NT-LPT-02", "NovaTech ProBook 15 G3", "Bilgisayar", 38500.0, 45),
            ("NT-SEC-03", "NovaShield Kurumsal Güvenlik Duvarı", "Güvenlik", 62000.0, 8),
            ("NT-SFT-04", "NovaERP Bulut Lisansı (Yıllık)", "Yazılım", 120000.0, 100),
            ("NT-MON-05", "NovaView 27 inç 4K Monitör", "Aksesuar", 9400.0, 60),
        ])

        cursor.executemany("""
        INSERT INTO satislar (siparis_no, musteri_adi, urun_id, adet, toplam_tutar, bolge, tarih) VALUES (?, ?, ?, ?, ?, ?, ?);
        """, [
            ("ORD-2026-001", "Anadolu Lojistik A.Ş.", 1, 2, 170000.0, "Marmara", "2026-01-15"),
            ("ORD-2026-002", "Başkent Sağlık Grubu", 2, 5, 192500.0, "İç Anadolu", "2026-01-18"),
            ("ORD-2026-003", "Ege Bilişim Teknolojileri", 3, 1, 62000.0, "Ege", "2026-02-02"),
            ("ORD-2026-004", "Akdeniz Perakende Ltd.", 4, 1, 120000.0, "Akdeniz", "2026-02-14"),
            ("ORD-2026-005", "Anadolu Lojistik A.Ş.", 5, 4, 37600.0, "Marmara", "2026-03-01"),
        ])

        cursor.executemany("""
        INSERT INTO destek_talepleri (talep_kodu, musteri_adi, konu, detay, cozum, durum) VALUES (?, ?, ?, ?, ?, ?);
        """, [
            ("SR-2026-101", "Anadolu Lojistik A.Ş.", "Sunucu BIOS Güncellemesi", "Enterprise Sunucu X1 yeniden başlatma sonrası IPMI bağlantısı kesildi.", "IPMI firmware 2.14 yaması uygulandı ve statik IP yeniden tanımlandı.", "Çözüldü"),
            ("SR-2026-102", "Başkent Sağlık Grubu", "ERP Lisans Aktivasyon Hatası", "Kullanıcılar eşzamanlı oturum açarken 'Lisans Limiti Aşıldı' uyarısı alıyor.", "Lisans sunucusundaki askıda kalan oturumlar sonlandırıldı ve havuz temizlendi.", "Çözüldü"),
            ("SR-2026-103", "Ege Bilişim Teknolojileri", "Güvenlik Duvarı VPN Yapılandırması", "Şube ofisleri arasında IPsec tüneli kurulurken IKEv2 anahtar uyuşmazlığı yaşandı.", "Faz-1 ve Faz-2 şifreleme algoritmaları AES-256 olarak eşitlendi.", "Çözüldü"),
        ])

    conn.commit()
    conn.close()
    return target_path
