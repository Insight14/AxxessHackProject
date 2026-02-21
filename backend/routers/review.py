from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.twelvelabs_client import TwelveLabsClient
from services.medication_extractor import extract_medications, get_medications
from config import TWELVELABS_INDEX_ID

router = APIRouter()
client = TwelveLabsClient()


class ApproveRequest(BaseModel):
    pass


class OverrideRequest(BaseModel):
    manual_text: str


@router.get("/review/pending")
async def list_pending_reviews():
    """Returns all recordings where medication_status = pending_review."""
    if not TWELVELABS_INDEX_ID:
        raise HTTPException(status_code=500, detail="TWELVELABS_INDEX_ID not set.")

    videos = await client.list_videos(TWELVELABS_INDEX_ID, filter_metadata={"medication_status": "pending_review"})

    results = []
    for video in videos:
        meta = video.get("user_metadata") or {}
        video_id = video.get("_id")
        medications = get_medications(video_id)
        if medications is None:
            # Trigger extraction on-demand if not cached
            try:
                medications = await extract_medications(video_id)
            except Exception:
                medications = []
        results.append({
            "video_id": video_id,
            "appointment_id": meta.get("appointment_id"),
            "patient_id": meta.get("patient_id"),
            "doctor_id": meta.get("doctor_id"),
            "medication_status": meta.get("medication_status"),
            "ai_medications": medications,
        })

    return {"pending": results}


@router.post("/review/{video_id}/approve")
async def approve_medications(video_id: str):
    """Doctor approves AI medication suggestions."""
    if not TWELVELABS_INDEX_ID:
        raise HTTPException(status_code=500, detail="TWELVELABS_INDEX_ID not set.")

    try:
        # Fetch current metadata
        videos = await client.list_videos(TWELVELABS_INDEX_ID)
        video = next((v for v in videos if v.get("_id") == video_id), None)
        if not video:
            raise HTTPException(status_code=404, detail="Video not found.")

        current_meta = dict(video.get("user_metadata") or {})
        current_meta["medication_status"] = "approved"
        current_meta.pop("medication_override_text", None)

        await client.update_video_metadata(TWELVELABS_INDEX_ID, video_id, current_meta)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"TwelveLabs error: {e}")

    return {"video_id": video_id, "status": "approved", "message": "Medication plan approved and visible to patient."}


@router.post("/review/{video_id}/override")
async def override_medications(video_id: str, body: OverrideRequest):
    """Doctor overrides AI suggestions with manual medication text."""
    if not TWELVELABS_INDEX_ID:
        raise HTTPException(status_code=500, detail="TWELVELABS_INDEX_ID not set.")

    try:
        videos = await client.list_videos(TWELVELABS_INDEX_ID)
        video = next((v for v in videos if v.get("_id") == video_id), None)
        if not video:
            raise HTTPException(status_code=404, detail="Video not found.")

        current_meta = dict(video.get("user_metadata") or {})
        current_meta["medication_status"] = "overridden"
        current_meta["medication_override_text"] = body.manual_text

        await client.update_video_metadata(TWELVELABS_INDEX_ID, video_id, current_meta)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"TwelveLabs error: {e}")

    return {
        "video_id": video_id,
        "status": "overridden",
        "override_text": body.manual_text,
        "message": "Doctor's medication plan saved and visible to patient.",
    }
