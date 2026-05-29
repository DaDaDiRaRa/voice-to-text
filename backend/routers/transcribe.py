from fastapi import APIRouter, UploadFile, File, HTTPException
from models.schemas import TranscribeResponse
from services.transcriber import transcribe_audio

router = APIRouter(prefix="/api", tags=["transcribe"])

ALLOWED_CONTENT_TYPES = {
    "audio/mpeg", "audio/mp4", "audio/wav", "audio/webm",
    "audio/ogg", "audio/flac", "application/octet-stream",
}
MAX_FILE_MB = 25


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(file: UploadFile = File(...)):
    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="지원하지 않는 오디오 형식입니다.")

    audio_bytes = await file.read()
    if len(audio_bytes) > MAX_FILE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"파일 크기는 {MAX_FILE_MB}MB 이하여야 합니다.")
    if len(audio_bytes) == 0:
        raise HTTPException(status_code=400, detail="빈 파일입니다.")

    transcript = await transcribe_audio(audio_bytes, filename=file.filename or "audio.webm")
    return TranscribeResponse(transcript=transcript)
