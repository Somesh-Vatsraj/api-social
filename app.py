from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl
from utils.detect_platform import detect_platform
from api.response import error_response
from extractors.generic import extract_media

app = FastAPI(title="Social Downloader API", version="1.0.0")
app.mount("/static", StaticFiles(directory="static"), name="static")

class DownloadRequest(BaseModel):
    url: HttpUrl

@app.get("/")
def home():
    return FileResponse("static/index.html")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/download")
def download(req: DownloadRequest):
    url = str(req.url)
    platform = detect_platform(url)
    if platform == "unknown":
        raise HTTPException(status_code=400, detail="Unsupported platform")
    try:
        return extract_media(url, platform)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=7860)
