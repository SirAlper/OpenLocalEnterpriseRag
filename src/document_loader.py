import os
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

    def _read_pdf(self, file_path: str) -> str:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text += content + "\n"
        return text

    def _read_docx(self, file_path: str) -> str:
        doc = Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs if p.text])

    def _read_txt(self, file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def load_and_chunk_file(self, file_path: str):
        """Tek bir belgeyi okur ve parçalar."""
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

        chunk_texts = self.text_splitter.split_text(content)
        for idx, chunk in enumerate(chunk_texts):
            chunk_id = f"{filename}_chunk_{idx}"
            chunks.append(chunk)
            ids.append(chunk_id)
            metadatas.append({"source": filename, "chunk_index": idx})

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