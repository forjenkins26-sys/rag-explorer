from groq import Groq

from config import GROQ_API_KEY, GROQ_MODEL

_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

SYSTEM_PROMPT = (
    "You are a RAG assistant. Answer the user's question using ONLY the "
    "provided context chunks. If the context does not contain the answer, "
    "say so plainly. Do not use outside knowledge. Cite chunk numbers you used."
)


def build_prompt(query: str, chunks: list[dict]) -> str:
    context = "\n\n".join(
        f"[Chunk #{c['chunk_number']} | {c['source']} p.{c['page']}]\n{c['content']}"
        for c in chunks
    )
    return f"Context:\n{context}\n\nQuestion: {query}"


def generate_answer(query: str, chunks: list[dict]) -> dict:
    prompt = build_prompt(query, chunks)

    if _client is None:
        return {
            "answer": (
                "[No GROQ_API_KEY / GROQ_KEY configured — set it in .env to enable "
                "LLM answer generation. Retrieved chunks above are still real.]"
            ),
            "prompt": prompt,
            "tokens": None,
        }

    completion = _client.chat.completions.create(
        model=GROQ_MODEL,
        temperature=0.3,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    usage = completion.usage
    return {
        "answer": completion.choices[0].message.content,
        "prompt": prompt,
        "tokens": usage.total_tokens if usage else None,
    }
