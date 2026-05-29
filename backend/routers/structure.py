from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from models.schemas import StructureRequest, StructureResponse, ExportRequest
from services.structurer import structure
from services import exporter
import io

router = APIRouter(prefix="/api", tags=["structure"])


@router.post("/structure", response_model=StructureResponse)
async def structure_transcript(req: StructureRequest):
    if not req.transcript.strip():
        raise HTTPException(status_code=400, detail="transcript가 비어 있습니다.")
    result = await structure(req.transcript, req.mode, req.metadata)
    return StructureResponse(mode=req.mode, result=result)


@router.post("/export/docx")
async def export_docx(req: ExportRequest):
    buf: io.BytesIO = exporter.to_docx(req.mode, req.result)
    filename = "회의록.docx" if req.mode == "meeting" else "현장메모.docx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
