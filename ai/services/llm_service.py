import anthropic
from django.conf import settings

from ai.constants import LLM_MODEL, MAX_TOKENS

_ASK_TEMPLATE = """\
You are a helpful assistant. Answer the following question clearly and concisely.

Question: {prompt}

Answer:"""

_RAG_TEMPLATE = """\
You are a helpful assistant. Answer the question using ONLY the provided context.
If the answer cannot be found in the context, say "I don't have enough context to answer that."

Context:
{context}

Question: {query}

Answer:"""


def _client():
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def ask(prompt: str) -> str:
    msg = _client().messages.create(
        model=LLM_MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": _ASK_TEMPLATE.format(prompt=prompt)}],
    )
    return msg.content[0].text


def rag_answer(query: str, chunks: list[str]) -> str:
    context = "\n\n".join(chunks)
    msg = _client().messages.create(
        model=LLM_MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": _RAG_TEMPLATE.format(context=context, query=query)}],
    )
    return msg.content[0].text
