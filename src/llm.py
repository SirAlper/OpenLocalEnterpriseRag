import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, pipeline
from langchain_huggingface import ChatHuggingFace, HuggingFacePipeline
from src.config import LLM_MODEL_NAME, USE_4BIT_QUANTIZATION


def create_chat_model() -> ChatHuggingFace:
    """Yerel Qwen modelini yükleyip LangChain ChatHuggingFace nesnesine dönüştürür.

    Dönen nesne standart LangChain ChatModel arayüzünü destekler:
        - chat_model.invoke(messages)  → Toplu yanıt
        - chat_model.stream(messages)  → Token bazlı canlı akış
        - chat_model.bind_tools(tools) → Araç bağlama (ileride)
    """
    is_cuda = torch.cuda.is_available()
    device_str = "CUDA GPU" if is_cuda else "CPU"
    print(f"Yerel Dil Modeli ({LLM_MODEL_NAME}) {device_str} üzerinde yükleniyor...")

    is_local = os.path.exists(LLM_MODEL_NAME)
    tokenizer = AutoTokenizer.from_pretrained(LLM_MODEL_NAME, local_files_only=is_local)

    # PyTorch 4-bit Kuantizasyon & Bellek Optimizasyonu
    quantization_config = None
    torch_dtype = torch.bfloat16 if is_cuda else torch.float32

    if is_cuda and USE_4BIT_QUANTIZATION:
        print("[PyTorch] 4-bit (NF4) Kuantizasyon aktif ediliyor...")
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16
        )

    model_kwargs = {
        "torch_dtype": torch_dtype,
        "device_map": "auto" if is_cuda else None,
        "local_files_only": is_local,
    }
    if quantization_config:
        model_kwargs["quantization_config"] = quantization_config
    elif is_cuda:
        model_kwargs["attn_implementation"] = "sdpa"

    model = AutoModelForCausalLM.from_pretrained(LLM_MODEL_NAME, **model_kwargs)

    # HuggingFace Pipeline → LangChain ChatModel dönüşümü
    print("[LangChain] HuggingFace Pipeline oluşturuluyor...")
    pipe = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=512,
        do_sample=False,
        repetition_penalty=1.05,
        return_full_text=False,
    )
    hf_llm = HuggingFacePipeline(pipeline=pipe)
    chat_model = ChatHuggingFace(llm=hf_llm)
    print("[LangChain] ChatHuggingFace modeli başarıyla oluşturuldu.")

    return chat_model
