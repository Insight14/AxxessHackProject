import json
from services.twelvelabs_client import TwelveLabsClient

client = TwelveLabsClient()

MEDICATION_PROMPT = """Extract all medications discussed in this doctor-patient conversation.
For each medication, provide:
1. name: Drug name (both generic and brand if mentioned)
2. dosage: Dosage if stated, else null
3. frequency: How often to take it, else null
4. purpose: Reason for prescribing, else null
5. instructions: Any warnings or special instructions given
6. video_start_seconds: Time in the video (in seconds) when first mentioned

Return ONLY a valid JSON array. If no medications were discussed, return [].
Example: [{"name":"Lisinopril","dosage":"10mg","frequency":"once daily","purpose":"blood pressure","instructions":"take in the morning","video_start_seconds":312}]"""

# In-memory store for medication suggestions keyed by video_id
_medication_store: dict[str, list] = {}


async def extract_medications(video_id: str) -> list:
    raw = await client.analyze_open_ended(video_id, MEDICATION_PROMPT, temperature=0.1)
    # raw may be the text content itself or a dict with a data key
    if isinstance(raw, dict):
        raw = raw.get("data", "")
    try:
        # Strip markdown code fences if present
        text = raw.strip().strip("```json").strip("```").strip()
        medications = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        medications = []
    _medication_store[video_id] = medications
    return medications


def get_medications(video_id: str) -> list | None:
    return _medication_store.get(video_id)
