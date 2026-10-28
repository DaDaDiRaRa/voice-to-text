"""
OpenAI gpt-4o-mini-transcribe를 사용한 한국어 STT.
25MB 초과 파일은 10분 단위로 자동 분할 후 청크별 STT → 결과 합산.
"""

import os
import tempfile
from pathlib import Path
from openai import AsyncOpenAI
from pydub import AudioSegment
from pydub.utils import mediainfo

from services.llm_usage import log_units

_client: AsyncOpenAI | None = None

SUPPORTED_EXTENSIONS = {".mp3", ".m4a", ".wav", ".webm", ".ogg", ".flac"}
OPENAI_LIMIT_BYTES = 23 * 1024 * 1024   # 여유 있게 23MB
CHUNK_DURATION_MS = 10 * 60 * 1000       # 10분


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable is not set")
        _client = AsyncOpenAI(api_key=api_key)
    return _client


async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        suffix = ".webm"

    if len(audio_bytes) <= OPENAI_LIMIT_BYTES:
        return await _transcribe_bytes(audio_bytes, filename, suffix)

    # 25MB 초과 → 청크 분할
    return await _transcribe_chunked(audio_bytes, suffix)


async def _transcribe_bytes(audio_bytes: bytes, filename: str, suffix: str,
                            duration_s: float | None = None) -> str:
    client = _get_client()

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            response = await client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=(filename, f, _mime_type(suffix)),
                language="ko",
                response_format="text",
            )
        _log_audio(tmp_path, len(audio_bytes), duration_s)
        return str(response).strip()
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _log_audio(path: str, n_bytes: int, duration_s: float | None) -> None:
    """STT 1회를 llm_usage 로 — 이 모델은 오디오 길이로 과금된다. text 응답엔 usage 가 없어
    길이를 파일 머리(ffprobe)에서 읽는다. 머리에 길이가 없는 녹음(브라우저 webm 등)은 None."""
    if duration_s is None:
        try:
            duration_s = round(float(mediainfo(path)["duration"]), 1)
        except Exception:  # noqa: BLE001 — 길이를 모르면 모른다고 남긴다
            duration_s = None
    log_units("voice-to-text", "openai", "gpt-4o-mini-transcribe",
              units={"audio_seconds": duration_s, "audio_bytes": n_bytes},
              meta={"purpose": "transcribe"})


async def _transcribe_chunked(audio_bytes: bytes, suffix: str) -> str:
    """pydub로 10분 단위 분할 → 각 청크 STT → 이어붙이기."""
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        src_path = tmp.name

    try:
        fmt = suffix.lstrip(".")
        if fmt == "m4a":
            fmt = "mp4"
        audio = AudioSegment.from_file(src_path, format=fmt)
    finally:
        Path(src_path).unlink(missing_ok=True)

    total_ms = len(audio)
    chunks = [
        audio[start : start + CHUNK_DURATION_MS]
        for start in range(0, total_ms, CHUNK_DURATION_MS)
    ]

    results: list[str] = []
    for i, chunk in enumerate(chunks):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            chunk_path = tmp.name

        try:
            chunk.export(chunk_path, format="mp3", parameters=["-q:a", "4"])
            chunk_bytes = Path(chunk_path).read_bytes()
            text = await _transcribe_bytes(chunk_bytes, f"chunk_{i}.mp3", ".mp3",
                                           duration_s=round(len(chunk) / 1000, 1))
            if text:
                results.append(text)
        finally:
            Path(chunk_path).unlink(missing_ok=True)

    return "\n".join(results)


def _mime_type(suffix: str) -> str:
    return {
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".wav": "audio/wav",
        ".webm": "audio/webm",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac",
    }.get(suffix, "audio/webm")
