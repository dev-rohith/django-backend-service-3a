from typing import TypedDict

from django.conf import settings
from langchain_anthropic import ChatAnthropic
from langgraph.graph import END, StateGraph

from agent.services.tools import rag_search, weather
from ai.constants import LLM_MODEL, MAX_TOKENS


class AgentState(TypedDict):
    messages: list[dict]
    query: str
    intent: str
    context: str
    sources: list[dict]
    response: str


def _llm() -> ChatAnthropic:
    return ChatAnthropic(
        model=LLM_MODEL,
        max_tokens=MAX_TOKENS,
        api_key=settings.ANTHROPIC_API_KEY,
    )


def _history_text(messages: list[dict], limit: int = 6) -> str:
    return "\n".join(
        f"{m['role'].capitalize()}: {m['content']}" for m in messages[-limit:]
    )


def classify_intent(state: AgentState) -> dict:
    history = _history_text(state["messages"])
    prompt = f"""\
Classify the user's intent into exactly one of: rag, weather, general.

- rag: asking about documents or uploaded content
- weather: asking about weather or temperature for a city
- general: anything else

Conversation:
{history}

User: {state["query"]}

Reply with ONE word only: rag, weather, or general."""

    result = _llm().invoke(prompt)
    intent = result.content.strip().lower()
    if intent not in ("rag", "weather", "general"):
        intent = "general"
    return {"intent": intent}


def rag_node(state: AgentState) -> dict:
    results, context = rag_search(state["query"])
    return {"context": context, "sources": results}


def weather_node(state: AgentState) -> dict:
    extract = _llm().invoke(
        f"Extract only the city name from this query. Reply with just the city name.\n"
        f"Query: {state['query']}"
    )
    city = extract.content.strip()
    data = weather(city)
    return {"context": data, "sources": []}


def general_node(state: AgentState) -> dict:
    return {"context": "", "sources": []}


def generate_response(state: AgentState) -> dict:
    history = _history_text(state["messages"])
    context = state["context"]

    if context:
        prompt = f"""\
You are a helpful assistant. Use the context below to answer the question.
If the context is weather data, describe it clearly.
If it is document excerpts, base your answer on them.

Conversation:
{history}

Context:
{context}

User: {state["query"]}
Assistant:"""
    else:
        prompt = f"""\
You are a helpful assistant. Answer conversationally.

Conversation:
{history}

User: {state["query"]}
Assistant:"""

    result = _llm().invoke(prompt)
    return {"response": result.content.strip()}


def _route(state: AgentState) -> str:
    return state["intent"]


def _build() -> object:
    g = StateGraph(AgentState)
    g.add_node("classify", classify_intent)
    g.add_node("rag", rag_node)
    g.add_node("weather", weather_node)
    g.add_node("general", general_node)
    g.add_node("respond", generate_response)

    g.set_entry_point("classify")
    g.add_conditional_edges("classify", _route, {
        "rag": "rag",
        "weather": "weather",
        "general": "general",
    })
    g.add_edge("rag", "respond")
    g.add_edge("weather", "respond")
    g.add_edge("general", "respond")
    g.add_edge("respond", END)

    return g.compile()


agent = _build()
