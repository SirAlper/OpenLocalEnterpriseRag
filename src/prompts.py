from langchain_core.messages import SystemMessage, HumanMessage


# ──────────────────────────── SİSTEM PROMPTLARI ────────────────────────────

SYSTEM_PROMPT_RAG = (
    "Sen kurumsal bir yapay zeka asistanısın.\n"
    "Sana sunulan Bağlamdaki şirket belgelerine birebir sadık kalarak, soruyu Türkçe, net, eksiksiz ve profesyonel bir şekilde yanıtla.\n"
    "Kurallar:\n"
    "1. Yalnızca soruyla DOĞRUDAN ilgili olan belge ve maddeleri yanıtla.\n"
    "2. Bağlamda soruyla ilgisiz farklı konulara ait bilgiler varsa (örneğin donanım, izin, bütçe vb.) bunları kesinlikle yanıta dahil etme.\n"
    "3. Belgede yer almayan hiçbir bilgiyi uydurma (halüsinasyon yapma).\n"
    "4. Cümleleri ve maddeleri eksiksiz, tam olarak bitir."
)

SYSTEM_PROMPT_GRADER = (
    "Sen bir denetçisin. Sana sunulan Bağlamdaki şirket belgelerini ve üretilen Cevabı incele.\n"
    "Cevaptaki tüm iddialar ve bilgiler Bağlam tarafından doğrulanıyor mu?\n"
    "Cevap doğrulanıyorsa sadece 'evet', belgede olmayan uydurma veya çelişen bilgi varsa sadece 'hayır' yaz. Başka hiçbir şey yazma."
)

NO_CONTEXT_RESPONSE = "Bu bilgi şirket belgelerinde bulunmamaktadır."

FALLBACK_RESPONSE = "Bu bilgi şirket belgelerinde tam olarak doğrulanamamaktadır."


# ──────────────────────────── MESAJ OLUŞTURMA ────────────────────────────

def build_rag_messages(context: str, question: str) -> list:
    """Kurumsal RAG yanıtı üretmek için LangChain mesaj listesi oluşturur."""
    return [
        SystemMessage(content=SYSTEM_PROMPT_RAG),
        HumanMessage(content=f"Bağlam:\n{context}\n\nSoru: {question}")
    ]


def build_grader_messages(context: str, question: str, answer: str) -> list:
    """Halüsinasyon denetimi için LangChain mesaj listesi oluşturur."""
    return [
        SystemMessage(content=SYSTEM_PROMPT_GRADER),
        HumanMessage(content=f"Bağlam:\n{context}\n\nSoru: {question}\n\nCevap:\n{answer}")
    ]
