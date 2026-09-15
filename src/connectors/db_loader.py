from typing import List, Dict, Any, Tuple, Optional
from src.connectors.db_connector import DatabaseConnector


class DatabaseTableLoader:
    """Veritabanı tablolarındaki metin kayıtlarını okuyup ChromaDB vektör motoruna

    aktarılabilir belgelere (chunk) dönüştüren evrensel ETL sınıfı.
    """

    def __init__(self, db_connector: DatabaseConnector):
        self.db = db_connector

    def load_table_as_chunks(
        self,
        table_name: str,
        text_columns: Optional[List[str]] = None,
        title_column: Optional[str] = None,
        id_column: Optional[str] = None
    ) -> Tuple[List[str], List[str], List[Dict[str, Any]]]:
        """Belirtilen tablodaki satırları okur, bağlamsal başlık ve etiketlerle zenginleştirip parçalara dönüştürür."""
        chunks = []
        ids = []
        metadatas = []

        if not self.db.is_connected or not self.db.engine:
            print("[DatabaseTableLoader] Veritabanı bağlantısı yok.")
            return chunks, ids, metadatas

        # Tabloyu sorgula
        query_result = self.db.execute_query(f"SELECT * FROM {table_name}")
        if query_result["status"] != "success":
            print(f"[DatabaseTableLoader] Hata: {query_result.get('message')}")
            return chunks, ids, metadatas

        rows = query_result.get("rows", [])
        columns = query_result.get("columns", [])

        if not rows:
            return chunks, ids, metadatas

        # Hedef kolonları belirle (özelleştirilmemişse tüm kolonlar)
        target_cols = text_columns if text_columns else columns

        # ID kolonunu tespit et (id_column verilmemişse 'id' içeren ilk kolonu ara)
        actual_id_col = id_column
        if not actual_id_col:
            for col in columns:
                if col.lower() in ("id", f"{table_name.lower()}_id", "pk"):
                    actual_id_col = col
                    break
            if not actual_id_col and columns:
                actual_id_col = columns[0]

        for idx, row in enumerate(rows):
            row_id_val = row.get(actual_id_col, idx + 1)
            chunk_id = f"db_{table_name}_row_{row_id_val}"

            # Başlık bilgisi
            title_text = f" | {row.get(title_column)}" if title_column and row.get(title_column) else ""
            header = f"[Veritabanı Tablosu: {table_name} | Kayıt: #{row_id_val}{title_text}]"

            # Satır içeriğini yapılandırılmış metne dönüştür
            row_content_lines = []
            for col in target_cols:
                val = row.get(col)
                if val is not None and str(val).strip():
                    row_content_lines.append(f"{col}: {val}")

            if not row_content_lines:
                continue

            full_chunk_text = f"{header}\n" + "\n".join(row_content_lines)

            chunks.append(full_chunk_text)
            ids.append(chunk_id)
            metadatas.append({
                "source": f"db_{table_name}",
                "chunk_index": idx,
                "document_title": header,
                "table_name": table_name,
                "record_id": str(row_id_val)
            })

        return chunks, ids, metadatas
