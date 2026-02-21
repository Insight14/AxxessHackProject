from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from routers import upload, summary, search, chapters, gist, review

app = FastAPI(title="Healthcare Conversation AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api")
app.include_router(summary.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(chapters.router, prefix="/api")
app.include_router(gist.router, prefix="/api")
app.include_router(review.router, prefix="/api")

# Serve frontend static files
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
