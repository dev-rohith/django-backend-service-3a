import requests

from ai.constants import TOP_K
from ai.services.vector_store import store


def weather(city: str) -> str:
    try:
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1},
            timeout=5,
        ).json()
        results = geo.get("results")
        if not results:
            return f"Could not find location: {city}"
        lat, lon = results[0]["latitude"], results[0]["longitude"]
        w = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": lat, "longitude": lon, "current_weather": True},
            timeout=5,
        ).json()
        c = w["current_weather"]
        return (
            f"Current weather in {city}: "
            f"Temperature {c['temperature']}°C, "
            f"Wind speed {c['windspeed']} km/h."
        )
    except Exception as exc:
        return f"Weather lookup failed: {exc}"


def rag_search(query: str) -> tuple[list[dict], str]:
    results = store.search(query, k=TOP_K)
    if not results:
        return [], ""
    context = "\n\n".join(r["chunk_text"] for r in results)
    return results, context
