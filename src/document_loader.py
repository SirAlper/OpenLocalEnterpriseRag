import os
import re
from pypdf import PdfReader
from docx import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

class DocumentLoader:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        # Metni parçalara bölerken anlam kopmasını önlemek için 100 karakter örtüşme (overlap) bırakıyoruz
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=600,
            chunk_overlap=100,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

    @staticmethod
    def _extract_document_header(content: str) -> str:
        """Belge metninin ilk satırlarından DOKÜMAN ve KOD bilgisini çıkararak bağlamsal başlık oluşturur.

        Örnek çıktı: '[Belge: NovaTech Bilgi Güvenliği ve Cihaz Kullanım Esasları | KOD: SEC-POL-04]'
        Başlık bulunamazsa dosya adından türetilmez; boş döner.
        """
        lines = content.strip().split("\n")[:5]  # İlk 5 satırı tara

        doc_title = ""
        doc_code = ""

        for line in lines:
            stripped = line.strip()
            # "DOKÜMAN:" veya "DOKÜMAN :" formatını yakala
            if re.match(r"^DOKÜMAN\s*:", stripped, re.IGNORECASE):
                doc_title = re.sub(r"^DOKÜMAN\s*:\s*", "", stripped, flags=re.IGNORECASE).strip()
            # "KOD:" veya "KOD :" formatını yakala
            elif re.match(r"^KOD\s*:", stripped, re.IGNORECASE):
                doc_code = re.sub(r"^KOD\s*:\s*", "", stripped, flags=re.IGNORECASE).strip()

        if doc_title and doc_code:
            return f"[Belge: {doc_title} | KOD: {doc_code}]"
        elif doc_title:
            return f"[Belge: {doc_title}]"

        return ""

    def _read_pdf(self, file_path: str) -> str:
        try:
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                content = page.extract_text()
                if content:
                    text += content + "\n"
            return text
        except Exception as e:
            print(f"[DocumentLoader] PDF okuma hatası ({os.path.basename(file_path)}): {e}")
            return ""

    def _read_docx(self, file_path: str) -> str:
        try:
            doc = Document(file_path)
            return "\n".join([p.text for p in doc.paragraphs if p.text])
        except Exception as e:
            print(f"[DocumentLoader] DOCX okuma hatası ({os.path.basename(file_path)}): {e}")
            return ""

    def _read_txt(self, file_path: str) -> str:
        try:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                return f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, "r", encoding="cp1254", errors="replace") as f:
                    return f.read()
            except Exception as e:
                print(f"[DocumentLoader] TXT okuma hatası ({os.path.basename(file_path)}): {e}")
                return ""
        except Exception as e:
            print(f"[DocumentLoader] TXT okuma hatası ({os.path.basename(file_path)}): {e}")
            return ""

    def load_and_chunk_file(self, file_path: str):
        """Tek bir belgeyi okur, başlık enjekte eder ve parçalar."""
        chunks = []
        ids = []
        metadatas = []

        if not os.path.isfile(file_path):
            return chunks, ids, metadatas

        filename = os.path.basename(file_path)
        ext = os.path.splitext(filename)[1].lower()

        content = ""
        if ext == ".pdf":
            content = self._read_pdf(file_path)
        elif ext == ".docx":
            content = self._read_docx(file_path)
        elif ext == ".txt":
            content = self._read_txt(file_path)
        else:
            print(f"Desteklenmeyen dosya formatı atlandı: {filename}")
            return chunks, ids, metadatas

        if not content.strip():
            return chunks, ids, metadatas

        # Bağlamsal başlığı çıkar (Contextual Chunking)
        doc_header = self._extract_document_header(content)

        chunk_texts = self.text_splitter.split_text(content)
        for idx, chunk in enumerate(chunk_texts):
            # Her parçanın başına belge başlığını enjekte et
            if doc_header and not chunk.strip().startswith("[Belge:"):
                contextualized_chunk = f"{doc_header}\n{chunk}"
            else:
                contextualized_chunk = chunk

            chunk_id = f"{filename}_chunk_{idx}"
            chunks.append(contextualized_chunk)
            ids.append(chunk_id)
            metadatas.append({
                "source": filename,
                "chunk_index": idx,
                "document_title": doc_header
            })

        return chunks, ids, metadatas

    def load_and_chunk_all(self):
        """data/ klasöründeki tüm geçerli belgeleri okur ve parçalar."""
        all_chunks = []
        all_ids = []
        metadatas = []

        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            return all_chunks, all_ids, metadatas

        for filename in os.listdir(self.data_dir):
            file_path = os.path.join(self.data_dir, filename)
            if not os.path.isfile(file_path):
                continue

            chunks, ids, metas = self.load_and_chunk_file(file_path)
            all_chunks.extend(chunks)
            all_ids.extend(ids)
            metadatas.extend(metas)

        return all_chunks, all_ids, metadatas