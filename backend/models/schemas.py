from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import date


class TranscribeResponse(BaseModel):
    transcript: str


class FieldMetadata(BaseModel):
    project_name: Optional[str] = None
    location: Optional[str] = None
    record_date: Optional[date] = None


class StructureRequest(BaseModel):
    transcript: str
    mode: Literal["meeting", "field"]
    metadata: Optional[FieldMetadata] = None


# Mode A — 회의록
class ActionItem(BaseModel):
    task: str
    assignee: Optional[str] = None
    due_date: Optional[str] = None


class MeetingStructure(BaseModel):
    agenda: list[str] = Field(default_factory=list, description="안건 목록")
    decisions: list[str] = Field(default_factory=list, description="결정사항")
    action_items: list[ActionItem] = Field(default_factory=list, description="액션아이템")
    summary: str = Field(description="논의 요약")


# Mode B — 현장 메모
class FieldNoteStructure(BaseModel):
    instructions: list[str] = Field(default_factory=list, description="업무 지시사항")
    check_items: list[str] = Field(default_factory=list, description="확인 필요 항목")
    observations: list[str] = Field(default_factory=list, description="현장 관찰 메모")
    tags: FieldMetadata = Field(default_factory=FieldMetadata)


class StructureResponse(BaseModel):
    mode: Literal["meeting", "field"]
    result: MeetingStructure | FieldNoteStructure


class ExportRequest(BaseModel):
    mode: Literal["meeting", "field"]
    result: dict
    format: Literal["docx", "pdf"] = "docx"
