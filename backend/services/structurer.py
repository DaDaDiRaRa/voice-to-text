"""
Claude Sonnet을 사용한 모드별 텍스트 구조화.

모드 A (meeting): 안건, 결정사항, 액션아이템, 논의 요약
모드 B (field):   업무 지시사항, 확인 필요 항목, 현장 관찰 메모
"""

import os
import json
from typing import Literal
from anthropic import AsyncAnthropic
from models.schemas import (
    MeetingStructure,
    FieldNoteStructure,
    FieldMetadata,
    ActionItem,
)

_client: AsyncAnthropic | None = None

MODEL = "claude-sonnet-4-6"


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set")
        _client = AsyncAnthropic(api_key=api_key)
    return _client


# ──────────────────────────────────────────────
# 모드 A — 회의록
# ──────────────────────────────────────────────

_MEETING_SYSTEM = """당신은 회의록 작성 전문가입니다.
사용자가 제공하는 회의 녹취 텍스트를 분석하여 아래 JSON 형식으로 정리하세요.

{
  "agenda": ["안건1", "안건2", ...],
  "decisions": ["결정사항1", "결정사항2", ...],
  "action_items": [
    {"task": "작업 내용", "assignee": "담당자 이름 또는 null", "due_date": "YYYY-MM-DD 또는 null"}
  ],
  "summary": "전체 논의 흐름을 3~5문장으로 요약한 텍스트"
}

규칙:
- 명확하지 않은 담당자·기한은 null로 표시
- 중복 항목 제거
- 한국어로 출력
- JSON만 반환 (마크다운 코드블록 없이)"""


async def structure_meeting(transcript: str) -> MeetingStructure:
    client = _get_client()
    response = await client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=_MEETING_SYSTEM,
        messages=[{"role": "user", "content": f"회의 녹취:\n\n{transcript}"}],
    )
    raw = response.content[0].text.strip()
    data = json.loads(raw)
    data["action_items"] = [ActionItem(**item) for item in data.get("action_items", [])]
    return MeetingStructure(**data)


# ──────────────────────────────────────────────
# 모드 B — 현장 메모
# ──────────────────────────────────────────────

_FIELD_SYSTEM = """당신은 현장 작업 메모 정리 전문가입니다.
사용자가 현장에서 혼자 말로 녹음한 메모를 아래 JSON 형식으로 정리하세요.

{
  "instructions": ["업무 지시사항1", ...],
  "check_items": ["확인 필요 항목1", ...],
  "observations": ["현장 관찰 메모1", ...]
}

규칙:
- 각 항목은 간결한 동작 문장으로 정리
- 중복 제거
- 한국어로 출력
- JSON만 반환 (마크다운 코드블록 없이)"""


async def structure_field(
    transcript: str, metadata: FieldMetadata | None = None
) -> FieldNoteStructure:
    client = _get_client()
    context = f"현장 메모 녹취:\n\n{transcript}"
    if metadata:
        parts = []
        if metadata.project_name:
            parts.append(f"프로젝트명: {metadata.project_name}")
        if metadata.location:
            parts.append(f"위치: {metadata.location}")
        if metadata.record_date:
            parts.append(f"날짜: {metadata.record_date}")
        if parts:
            context = "\n".join(parts) + "\n\n" + context

    response = await client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=_FIELD_SYSTEM,
        messages=[{"role": "user", "content": context}],
    )
    raw = response.content[0].text.strip()
    data = json.loads(raw)
    return FieldNoteStructure(**data, tags=metadata or FieldMetadata())


# ──────────────────────────────────────────────
# 통합 진입점
# ──────────────────────────────────────────────

async def structure(
    transcript: str,
    mode: Literal["meeting", "field"],
    metadata: FieldMetadata | None = None,
) -> MeetingStructure | FieldNoteStructure:
    if mode == "meeting":
        return await structure_meeting(transcript)
    return await structure_field(transcript, metadata)
