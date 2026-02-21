from fastapi import APIRouter, HTTPException
from services.twelvelabs_client import TwelveLabsClient

router = APIRouter()
client = TwelveLabsClient()


@router.get("/gist/{video_id}")
async def get_gist(video_id: str):
    try:
        gist = await client.generate_gist(video_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"TwelveLabs error: {e}")

    return {
        "video_id": video_id,
        "title": gist.get("title", ""),
        "topics": gist.get("topics", []),
        "hashtags": gist.get("hashtags", []),
    }
