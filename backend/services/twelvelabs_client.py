import asyncio
import json
import httpx
from config import (
    TWELVELABS_API_KEY,
    TWELVELABS_BASE_URL,
    POLL_INTERVAL_SECONDS,
    POLL_MAX_ATTEMPTS,
)


HEADERS = {
    "x-api-key": TWELVELABS_API_KEY,
    "Accept": "application/json",
}


class TwelveLabsClient:
    def __init__(self):
        self.base_url = TWELVELABS_BASE_URL
        self.headers = HEADERS

    # -------------------------------------------------------------------------
    # Index management
    # -------------------------------------------------------------------------

    async def create_index(self, index_name: str) -> dict:
        payload = {
            "index_name": index_name,
            "models": [
                {"model_name": "pegasus1.2", "model_options": ["visual", "audio"]},
                {"model_name": "marengo3.0", "model_options": ["visual", "audio"]},
            ],
            "addons": ["thumbnail"],
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.base_url}/indexes",
                headers={**self.headers, "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

    # -------------------------------------------------------------------------
    # Upload & indexing
    # -------------------------------------------------------------------------

    async def create_task(
        self, index_id: str, video_bytes: bytes, filename: str, user_metadata: dict
    ) -> dict:
        files = {"video_file": (filename, video_bytes, "video/mp4")}
        data = {
            "index_id": index_id,
            "enable_video_stream": "true",
            "user_metadata": json.dumps(user_metadata),
        }
        async with httpx.AsyncClient(timeout=600) as client:
            resp = await client.post(
                f"{self.base_url}/tasks",
                headers=self.headers,
                files=files,
                data=data,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_task_status(self, task_id: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base_url}/tasks/{task_id}",
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def wait_until_ready(self, task_id: str) -> str:
        """Poll until status == 'ready'. Returns video_id."""
        for _ in range(POLL_MAX_ATTEMPTS):
            data = await self.get_task_status(task_id)
            status = data.get("status")
            if status == "ready":
                return data.get("video_id", data.get("_id"))
            if status == "failed":
                raise RuntimeError(f"TwelveLabs task {task_id} failed: {data}")
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
        raise TimeoutError(f"Task {task_id} did not complete in time.")

    # -------------------------------------------------------------------------
    # Video metadata
    # -------------------------------------------------------------------------

    async def list_videos(self, index_id: str, filter_metadata: dict | None = None) -> list:
        params: dict = {"index_id": index_id, "page_limit": 50}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base_url}/indexes/{index_id}/videos",
                headers=self.headers,
                params=params,
            )
            resp.raise_for_status()
            videos = resp.json().get("data", [])
        if filter_metadata:
            # Client-side filter on user_metadata fields
            def matches(v):
                meta = v.get("user_metadata") or {}
                return all(meta.get(k) == str(val) for k, val in filter_metadata.items())
            videos = [v for v in videos if matches(v)]
        return videos

    async def update_video_metadata(self, index_id: str, video_id: str, user_metadata: dict) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.patch(
                f"{self.base_url}/indexes/{index_id}/videos/{video_id}",
                headers={**self.headers, "Content-Type": "application/json"},
                json={"user_metadata": user_metadata},
            )
            resp.raise_for_status()
            return resp.json() if resp.text else {}

    # -------------------------------------------------------------------------
    # Generation: summary, chapters, gist, open-ended analyze
    # -------------------------------------------------------------------------

    async def generate_summary(self, video_id: str, prompt: str, temperature: float = 0.3) -> str:
        payload = {
            "video_id": video_id,
            "type": "summary",
            "prompt": prompt,
            "temperature": temperature,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.base_url}/summarize",
                headers={**self.headers, "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            return resp.json().get("summary", "")

    async def generate_chapters(self, video_id: str, prompt: str) -> list:
        payload = {
            "video_id": video_id,
            "type": "chapter",
            "prompt": prompt,
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.base_url}/summarize",
                headers={**self.headers, "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            return resp.json().get("chapters", [])

    async def generate_gist(self, video_id: str) -> dict:
        payload = {"video_id": video_id, "types": ["title", "topic", "hashtag"]}
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.base_url}/gist",
                headers={**self.headers, "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

    async def analyze_open_ended(self, video_id: str, prompt: str, temperature: float = 0.1) -> str:
        payload = {
            "video_id": video_id,
            "prompt": prompt,
            "temperature": temperature,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.base_url}/analyze",
                headers={**self.headers, "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            return resp.json().get("data", "")

    # -------------------------------------------------------------------------
    # Search
    # -------------------------------------------------------------------------

    async def search(
        self,
        index_id: str,
        query_text: str,
        filter_metadata: dict | None = None,
        search_options: list | None = None,
        page_limit: int = 5,
    ) -> list:
        payload: dict = {
            "index_id": index_id,
            "query_text": query_text,
            "search_options": search_options or ["audio"],
            "group_by": "clip",
            "threshold": "medium",
            "page_limit": page_limit,
        }
        if filter_metadata:
            payload["filter"] = {"user_metadata": filter_metadata}
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.base_url}/search",
                headers={**self.headers, "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            return resp.json().get("data", [])
