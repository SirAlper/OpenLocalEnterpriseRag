import streamlit as st
import requests
import json

API_BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Enterprise Local RAG",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Stil özelleştirmeleri
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #6c757d;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 12px;
        border-left: 4px solid #009688;
        margin-bottom: 10px;
    }
    .source-box {
        background-color: rgba(0, 150, 136, 0.08);
        border-radius: 6px;
        padding: 10px;
        margin-top: 8px;
        border-left: 3px solid #009688;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)


# API Yardımcı Fonksiyonları
def fetch_stats():
    try:
        res = requests.get(f"{API_BASE_URL}/api/v1/stats", timeout=5)
        if res.status_code == 200:
            return res.json()
    except Exception:
        return None
    return None


def fetch_documents():
    try:
        res = requests.get(f"{API_BASE_URL}/api/v1/documents", timeout=5)
        if res.status_code == 200:
            return res.json().get("documents", [])
    except Exception:
        return []
    return []


def upload_document(uploaded_file):
    try:
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
        res = requests.post(f"{API_BASE_URL}/api/v1/upload-file", files=files, timeout=60)
        return res.status_code == 200, res.json().get("message", "Bilinmeyen yanıt.")
    except Exception as e:
        return False, str(e)


def delete_document_api(filename):
    try:
        res = requests.delete(f"{API_BASE_URL}/api/v1/documents/{filename}", timeout=10)
        return res.status_code == 200, res.json().get("message", "Silindi.")
    except Exception as e:
        return False, str(e)


def query_rag_api(question):
    try:
        res = requests.post(
            f"{API_BASE_URL}/api/v1/query",
            json={"question": question},
            timeout=180
        )
        if res.status_code == 200:
            return res.json()
        return {"status": "error", "answer": f"Hata oluştu: {res.text}", "sources": []}
    except Exception as e:
        return {"status": "error", "answer": f"API Bağlantı Hatası: {e}", "sources": []}


def stream_rag_api(question):
    """FastAPI canlı akış endpoint'inden token ve kaynak verilerini çeker."""
    try:
        with requests.post(
            f"{API_BASE_URL}/api/v1/query-stream",
            json={"question": question},
            stream=True,
            timeout=180
        ) as res:
            if res.status_code == 200:
                for line in res.iter_lines(decode_unicode=True):
                    if line:
                        try:
                            yield json.loads(line)
                        except Exception:
                            continue
            else:
                yield {"type": "token", "token": f"Hata oluştu: {res.text}"}
    except Exception as e:
        yield {"type": "token", "token": f"API Bağlantı Hatası: {e}"}


# --- OTURUM DURUMU (SESSION STATE) ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Merhaba! Ben yerel kurumsal yapay zeka asistanınızım. Şirket içi belgelerinizle ilgili sorularınızı yanıtlayabilirim.",
            "sources": []
        }
    ]


# --- SOL YAN PANEL (SIDEBAR) ---
with st.sidebar:
    st.title("⚙️ Yönetim Paneli")

    # 1. Sistem Durumu
    stats = fetch_stats()
    if stats:
        st.success("🟢 API Bağlantısı Aktif")
        st.markdown(f"**Cihaz:** `{stats.get('device', 'Bilinmiyor')}`")
        st.markdown(f"**Model:** `{stats.get('llm_model', '').split('/')[-1]}`")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Toplam Belge", stats.get("total_documents", 0))
        with col2:
            st.metric("Vektör Parçası", stats.get("total_chunks", 0))
    else:
        st.error("🔴 API Çevrimdışı (FastAPI başlatılmamış)")
        st.info("Terminalde: `uvicorn src.main:app --reload` komutunu çalıştırın.")

    st.divider()

    # 2. Belge Yükleme
    st.subheader("📤 Belge Yükle")
    uploaded_file = st.file_uploader(
        "PDF, Word veya Metin belgesi seçin",
        type=["pdf", "docx", "txt"],
        help="Yüklenen dosya otomatik olarak parçalanıp ChromaDB'ye kaydedilir."
    )
    if uploaded_file is not None:
        if st.button("🚀 Yükle ve İndeksle", use_container_width=True):
            with st.spinner("Belge ayrıştırılıyor ve vektörleştiriliyor..."):
                success, msg = upload_document(uploaded_file)
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(f"Yükleme hatası: {msg}")

    st.divider()

    # 3. Yüklü Belgeler Listesi & Silme
    st.subheader("📚 İndekslenmiş Belgeler")
    docs = fetch_documents()
    if docs:
        for doc in docs:
            col_info, col_del = st.columns([4, 1])
            with col_info:
                st.markdown(f"**{doc['filename']}**  \n<small>{doc['size_kb']} KB | {doc['chunk_count']} parça</small>", unsafe_allow_html=True)
            with col_del:
                if st.button("🗑️", key=f"del_{doc['filename']}", help=f"'{doc['filename']}' dosyasını sil"):
                    success, msg = delete_document_api(doc['filename'])
                    if success:
                        st.toast(f"'{doc['filename']}' silindi!", icon="🗑️")
                        st.rerun()
                    else:
                        st.error(msg)
            st.write("---")
    else:
        st.caption("Henüz yüklenmiş bir belge bulunmuyor.")

    st.divider()
    if st.button("🧹 Sohbeti Temizle", use_container_width=True):
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Sohbet geçmişi temizlendi. Yeni sorularınızı bekliyorum!",
                "sources": []
            }
        ]
        st.rerun()


# --- ANA PANEL (CHAT) ---
st.markdown('<div class="main-header">🏢 Enterprise Local RAG Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Tamamen yerel donanımda çalışan, veri sızıntısı riski olmayan kurumsal yapay zeka asistanı.</div>', unsafe_allow_html=True)

# Mesaj Geçmişini Ekrana Bas
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        
        # Doğruluk denetimi rozeti
        if msg.get("verified") is True:
            st.caption("🛡️ *LangGraph Denetimi: Şirket belgeleriyle doğrulandı.*")
        elif msg.get("verified") is False:
            st.caption("⚠️ *LangGraph Denetimi: Belgelerle tam doğrulanamadı.*")

        # Referans alınan kaynaklar varsa expander içinde göster
        if msg.get("sources"):
            with st.expander(f"📚 Referans Alınan Kaynaklar ({len(msg['sources'])} Parça)"):
                for idx, src in enumerate(msg["sources"], 1):
                    distance_info = f" (Mesafe: {src['distance']})" if src.get("distance") is not None else ""
                    st.markdown(f"**{idx}. 📄 `{src['source']}` — Parça #{src['chunk_index']}{distance_info}**")
                    st.markdown(f"> *\"{src['content'].strip()}\"*")
                    st.write("")

# Yeni Kullanıcı Sorusu
if prompt := st.chat_input("Şirket belgeleriniz hakkında bir soru sorun (ör. 'Yıllık izin politikamız nedir?')..."):
    # Kullanıcı mesajını ekle
    st.session_state.messages.append({"role": "user", "content": prompt, "sources": []})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Modelden yanıt al (Canlı Streaming)
    with st.chat_message("assistant"):
        sources = []
        full_answer = []
        verified = None
        warning_msg = None

        def response_generator():
            nonlocal verified, warning_msg
            for event in stream_rag_api(prompt):
                event_type = event.get("type")
                if event_type == "sources":
                    sources.extend(event.get("sources", []))
                elif event_type == "token":
                    token = event.get("token", "")
                    full_answer.append(token)
                    yield token
                elif event_type == "grade":
                    verified = event.get("passed", True)
                elif event_type == "warning":
                    warning_msg = event.get("message", "")

        # Streamlit st.write_stream ile canlı akışı ekrana bas
        st.write_stream(response_generator())

        # Uyarı veya Doğrulama rozeti
        if warning_msg:
            st.warning(warning_msg)
        elif verified is True and sources:
            st.caption("🛡️ *LangGraph Denetimi: Şirket belgeleriyle doğrulandı.*")

        # Kaynakları göster
        if sources:
            with st.expander(f"📚 Referans Alınan Kaynaklar ({len(sources)} Parça)"):
                for idx, src in enumerate(sources, 1):
                    distance_info = f" (Mesafe: {src['distance']})" if src.get("distance") is not None else ""
                    st.markdown(f"**{idx}. 📄 `{src['source']}` — Parça #{src['chunk_index']}{distance_info}**")
                    st.markdown(f"> *\"{src['content'].strip()}\"*")
                    st.write("")

        # Asistan mesajını geçmişe kaydet
        st.session_state.messages.append({
            "role": "assistant",
            "content": "".join(full_answer),
            "sources": sources,
            "verified": verified
        })
