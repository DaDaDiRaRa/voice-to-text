"""
OpenAI gpt-4o-mini-transcribe를 사용한 한국어 STT.

Usage:
    from services.transcriber import transcribe_audio
    transcript = await transcribe_audio(audio_bytes, filename="recording.webm")
"""

import os
import tempfile
from pathlib import Path
from openai import AsyncOpenAI

_client: AsyncOpenAI | None = None

SUPPORTED_EXTENSIONS = {".mp3", ".m4a", ".wav", ".webm", ".ogg", ".flac"}


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable is not set")
        _client = AsyncOpenAI(api_key=api_key)
    return _client


async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    """
    오디오 bytes를 받아 한국어 텍스트로 변환합니다.

    Args:
        audio_bytes: 오디오 파일의 raw bytes
        filename: 원본 파일명 (확장자로 MIME 타입 결정)

    Returns:
        변환된 한국어 텍스트
    """
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        # 지원하지 않는 형식은 webm으로 fallback
        suffix = ".webm"

    client = _get_client()

    # OpenAI SDK는 file-like object를 요구하므로 임시 파일 사용
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as audio_file:
            response = await client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=(filename, audio_file, _mime_type(suffix)),
                language="ko",
                response_format="text",
            )
        # response_format="text" → 반환값이 str
        return str(response).strip()
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _mime_type(suffix: str) -> str:
    return {
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".wav": "audio/wav",
        ".webm": "audio/webm",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac",
    }.get(suffix, "audio/webm")
