import os

import httpx


class Client:
    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        timeout: float = 10.0,
    ):
        self.base_url = base_url or os.environ.get("API_BASE_URL", "http://localhost:8000")
        self.token = token or os.environ.get("API_TOKEN")
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        self._client = httpx.Client(base_url=self.base_url, headers=headers, timeout=timeout)

    def get(self, path: str, **kwargs):
        return self._client.get(path, **kwargs).json()

    def post(self, path: str, json=None, **kwargs):
        return self._client.post(path, json=json, **kwargs).json()

    def close(self):
        self._client.close()
