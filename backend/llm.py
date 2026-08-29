import re

from groq import Groq

from config import GROQ_API_KEY, GROQ_MODEL

_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

SYSTEM_PROMPT = (
    "You are a RAG assistant. Answer the user's question using ONLY the "
    "provided context chunks. If the context does not contain the answer, "
    "say so plainly. Do not use outside knowledge.\n"
    "\n"
    "Cite sources as plain text in square brackets, naming the chunk number "
    "exactly as it appears in the context — for example [Chunk #2], or "
    "[Chunk #1, #3] for several. Never invent line numbers, and never use any "
    "other citation notation: no daggers, no CJK brackets, no footnote marks. "
    "A citation that does not match a chunk number given above is wrong."
)


# gpt-oss emits its own trained citation format — 【3†L1-L4】 — whatever the
# system prompt asks for. Those markers point at line numbers that do not exist
# in our chunks, so they are noise the reader cannot act on. Rewrite the ones
# carrying a usable chunk number into [Chunk #N] and drop the rest. The prompt
# asks for the right format; this guarantees it.
_CJK_CITATION = re.compile(r"【([^】]*)】")


def strip_model_citations(text: str) -> str:
    """Normalise the model's citation markers to plain [Chunk #N] text."""

    def replace(match: re.Match) -> str:
        inner = match.group(1)
        # "3†L1-L4" -> chunk 3; "1†L1-L2, 3†L9" -> chunks 1 and 3
        nums = re.findall(r"(\d+)\s*†", inner) or re.findall(r"^(\d+)$", inner.strip())
        if not nums:
            return ""
        seen = list(dict.fromkeys(nums))
        return " [Chunk #" + ", #".join(seen) + "]"

    cleaned = _CJK_CITATION.sub(replace, text)
    # Collapse the double spaces the substitution can leave, and pull any
    # punctuation back against the citation it follows.
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"[ \t]+([.,;:])", r"\1", cleaned)
    return cleaned.strip()


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
        "answer": strip_model_citations(completion.choices[0].message.content or ""),
        "prompt": prompt,
        "tokens": usage.total_tokens if usage else None,
    }
