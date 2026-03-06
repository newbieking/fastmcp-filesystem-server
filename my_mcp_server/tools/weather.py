# src/my_mcp_server/tools/weather.py
from typing import Protocol
import httpx


class WeatherService(Protocol):
    async def get_current(self, city: str) -> dict: ...


class OpenWeatherService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5"

    async def get_current(self, city: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/weather",
                params={"q": city, "appid": self.api_key, "units": "metric"}
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "temp": data["main"]["temp"],
                "description": data["weather"][0]["description"],
                "humidity": data["main"]["humidity"]
            }


