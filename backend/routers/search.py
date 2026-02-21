from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.twelvelabs_client import TwelveLabsClient
from config import TWELVELABS_INDEX_ID

router = APIRouter()
client = TwelveLabsClient()


class SearchRequest(BaseModel):
    query: str
    appointment_id: str | None = None
    patient_id: str | None = None
    page_limit: int = 5


@router.post("/search")
async def search_recording(req: SearchRequest):
    if not TWELVELABS_INDEX_ID:
        raise HTTPException(status_code=500, detail="TWELVELABS_INDEX_ID not set.")

    filter_metadata: dict = {}
    if req.appointment_id:
        filter_metadata["appointment_id"] = req.appointment_id
    if req.patient_id:
        filter_metadata["patient_id"] = req.patient_id

    try:
        clips = await client.search(
            index_id=TWELVELABS_INDEX_ID,
            query_text=req.query,
            filter_metadata=filter_metadata or None,
            search_options=["audio"],
            page_limit=req.page_limit,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"TwelveLabs error: {e}")

    results = [
        {
            "video_id": clip.get("video_id"),
            "start": clip.get("start"),
            "end": clip.get("end"),
            "score": clip.get("score"),
            "confidence": clip.get("confidence"),
            "transcription": clip.get("transcription", ""),
        }
        for clip in clips
    ]

    return {"query": req.query, "results": results}
