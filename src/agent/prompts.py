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
    "Cevaptaki olgular ve temel iddialar Bağlam tarafından doğrulanıyor mu?\n"
    "Özetleme veya farklı sözcüklerle ifade etme (paraphrase) halüsinasyon değildir.\n"
    "Cevap doğrulanıyorsa sadece 'evet', belgede olmayan uydurma veya çelişen bilgi varsa sadece 'hayır' yaz. Başka hiçbir şey yazma."
)

SYSTEM_PROMPT_REFINE = (
    "Sen kurumsal bir editör ve doğrulama uzmanısın.\n"
    "Sana sunulan Bağlamı, Soruyu ve daha önce üretilmiş Taslak Cevabı incele.\n"
    "Taslak cevapta şirket belgeleriyle tam örtüşmeyen veya bağlam dışı kalmış kısımlar olabilir.\n"
    "Görevin:\n"
    "1. Taslak cevaptan belgede doğrudan yer almayan tüm uydurma, abartılı veya desteksiz kısımları tamamen çıkar (buda).\n"
    "2. Yalnızca Bağlam tarafından açıkça doğrulanan bilgileri koruyarak Türkçe, net ve profesyonel bir yanıt oluştur.\n"
    "3. Eğer bağlamda soruyu yanıtlayacak doğrulanabilir hiçbir bilgi yoksa, yalnızca 'Bu bilgi şirket belgelerinde bulunmamaktadır.' yaz.\n"
    "4. Cümleleri eksiksiz ve düzgün tamamla."
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


def build_refine_messages(context: str, question: str, draft_answer: str) -> list:
    """Doğrulanmamış veya şüpheli yanıtı bağlama sadık kalarak yeniden düzenlemek için mesaj listesi oluşturur."""
    return [
        SystemMessage(content=SYSTEM_PROMPT_REFINE),
        HumanMessage(content=f"Bağlam:\n{context}\n\nSoru: {question}\n\nİncelenecek Taslak Cevap:\n{draft_answer}")
    ]

