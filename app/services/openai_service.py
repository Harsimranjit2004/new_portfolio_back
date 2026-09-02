import json
from collections.abc import AsyncIterator

import httpx
from fastapi import HTTPException, status

from ..config import get_settings


class OpenAICompatibleClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.settings.openai_api_key}", "Content-Type": "application/json"}

    def _require(self, model: str) -> None:
        if not self.settings.openai_api_key or not model:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="OpenAI-compatible API is not configured")

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self.settings.openai_embedding_model
        self._require(model)
        url = f"{self.settings.openai_base_url.rstrip('/')}/embeddings"
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, headers=self._headers(), json={"model": model, "input": texts})
        if response.is_error:
            raise HTTPException(status_code=502, detail=f"Embedding provider error: {response.text[:500]}")
        data = sorted(response.json().get("data", []), key=lambda item: item.get("index", 0))
        if len(data) != len(texts):
            raise HTTPException(status_code=502, detail="Embedding provider returned an unexpected result count")
        return [item["embedding"] for item in data]

    async def chat(self, messages: list[dict[str, str]]) -> str:
        model = self.settings.openai_model
        self._require(model)
        url = f"{self.settings.openai_base_url.rstrip('/')}/chat/completions"
        payload = {"model": model, "messages": messages, "temperature": 0.15, "max_tokens": 700}
        async with httpx.AsyncClient(timeout=75) as client:
            response = await client.post(url, headers=self._headers(), json=payload)
        if response.is_error:
            raise HTTPException(status_code=502, detail=f"Chat provider error: {response.text[:500]}")
        try:
            return response.json()["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise HTTPException(status_code=502, detail="Chat provider returned an unexpected response") from exc

    async def stream_chat(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        model = self.settings.openai_model
        self._require(model)
        url = f"{self.settings.openai_base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.15,
            "max_tokens": 700,
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=75) as client:
            async with client.stream("POST", url, headers=self._headers(), json=payload) as response:
                if response.is_error:
                    detail = (await response.aread()).decode(errors="replace")[:500]
                    raise HTTPException(status_code=502, detail=f"Chat provider error: {detail}")

                data_lines: list[str] = []
                async for line in response.aiter_lines():
                    if not line:
                        if data_lines:
                            event_data = "\n".join(data_lines)
                            data_lines.clear()
                            if event_data == "[DONE]":
                                return
                            yield self._delta_content(event_data)
                        continue
                    if line.startswith(":"):
                        continue
                    field, separator, value = line.partition(":")
                    if field == "data":
                        data_lines.append(value[1:] if separator and value.startswith(" ") else value)

                if data_lines:
                    event_data = "\n".join(data_lines)
                    if event_data != "[DONE]":
                        yield self._delta_content(event_data)

    @staticmethod
    def _delta_content(event_data: str) -> str:
        try:
            payload = json.loads(event_data)
            if payload.get("error"):
                error = payload["error"]
                detail = error.get("message") if isinstance(error, dict) else str(error)
                raise HTTPException(status_code=502, detail=f"Chat provider error: {detail}")
            content = payload["choices"][0]["delta"].get("content")
            return content if isinstance(content, str) else ""
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise HTTPException(status_code=502, detail="Chat provider returned an invalid stream event") from exc
