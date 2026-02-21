import os
from dotenv import load_dotenv

load_dotenv()

TWELVELABS_API_KEY = os.getenv("TWELVELABS_API_KEY", "tlk_06YJPCA049YHJ82K8WWZ80QV9GE2")
TWELVELABS_BASE_URL = "https://api.twelvelabs.io/v1.3"
TWELVELABS_INDEX_ID = os.getenv("TWELVELABS_INDEX_ID", "")

MAX_VIDEO_SIZE_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB
POLL_INTERVAL_SECONDS = 10
POLL_MAX_ATTEMPTS = 180  # 30 minutes max
