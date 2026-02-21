from fastapi import APIRouter, HTTPException
from services.twelvelabs_client import TwelveLabsClient

router = APIRouter()
client = TwelveLabsClient()

CHAPTER_PROMPT = (
    "Segment this doctor-patient conversation into logical sections. "
    "Use chapter titles that a patient can understand, such as: "
    "'Checking Your Symptoms', 'Test Results Explained', "
    "'Your Medication Plan', 'What To Do Before Next Visit'. "
    "Avoid clinical abbreviations. Write chapter summaries in plain, friendly English."
)


@router.get("/chapters/{video_id}")
async def get_chapters(video_id: str):
    try:
        chapters = await client.generate_chapters(video_id, CHAPTER_PROMPT)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"TwelveLabs error: {e}")

    return {"video_id": video_id, "chapters": chapters}
