from typing import Any

import httpx
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    rest_api_base_url: str = ""


settings = Settings()


class RESTClient:
    def __init__(self, base_url: str | None = None, token: str | None = None):
        self.base_url = base_url or settings.rest_api_base_url
        self._client = httpx.AsyncClient(base_url=self.base_url)
        self._token = token

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        headers = kwargs.pop("headers", {})
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        response = await self._client.request(method, path, headers=headers, **kwargs)
        response.raise_for_status()
        return response.json()

    async def get(self, path: str, **kwargs: Any) -> Any:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> Any:
        return await self.request("POST", path, **kwargs)


# convenience singleton; in tests you can monkeypatch its methods
client = RESTClient()
