from openai import OpenAI
import os

_client: OpenAI | None = None
_API_KEY_PLACEHOLDER = "your_siliconflow_api_key_here"


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=os.getenv("LLM_API_KEY", ""),
            base_url=os.getenv("LLM_BASE_URL", "https://api.siliconflow.cn/v1"),
        )
    return _client


def _build_prompt(question: str, contexts: list[dict]) -> str:
    context_text = "\n\n".join(
        f"【{c['doc_name']} 第{c['page_num']}页】\n{c['text']}"
        for c in contexts
    )
    return (
        "你是一个课程助手，请根据以下教材原文回答学生的问题。\n"
        "要求：\n"
        "- 只使用提供的教材内容作答，不要编造信息\n"
        "- 回答要条理清晰，对于有多个要点的问题请分点列出\n"
        "- 用自己的语言归纳解释，不要逐字复制教材原文\n"
        "- 如果学生输入的是概念名称或术语而非完整问题，请解释该概念的定义和要点\n"
        "- 如果教材中没有相关内容，直接说明【教材中未涉及此内容】\n\n"
        f"教材内容：\n{context_text}\n\n"
        f"学生问题：{question}\n\n"
        "回答："
    )


def generate_answer(question: str, contexts: list[dict]) -> str:
    api_key = os.getenv("LLM_API_KEY", "")
    if not api_key or api_key == _API_KEY_PLACEHOLDER:
        return ""
    model = os.getenv("LLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")
    response = _get_client().chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": _build_prompt(question, contexts)}],
        max_tokens=800,
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


def generate_answer_stream(question: str, contexts: list[dict]):
    api_key = os.getenv("LLM_API_KEY", "")
    if not api_key or api_key == _API_KEY_PLACEHOLDER:
        return
    model = os.getenv("LLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")
    stream = _get_client().chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": _build_prompt(question, contexts)}],
        max_tokens=800,
        temperature=0.3,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content
