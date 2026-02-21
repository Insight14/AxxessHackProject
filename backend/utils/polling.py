import asyncio
from services.twelvelabs_client import TwelveLabsClient


async def poll_until_ready(task_id: str) -> str:
    """Polls TwelveLabs until the task is ready. Returns video_id."""
    client = TwelveLabsClient()
    return await client.wait_until_ready(task_id)
