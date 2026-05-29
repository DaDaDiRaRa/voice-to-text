const BASE = import.meta.env.VITE_API_BASE ?? "/api";

export type Mode = "meeting" | "field";

export interface FieldMetadata {
  project_name?: string;
  location?: string;
  record_date?: string; // YYYY-MM-DD
}

export interface ActionItem {
  task: string;
  assignee: string | null;
  due_date: string | null;
}

export interface MeetingResult {
  agenda: string[];
  decisions: string[];
  action_items: ActionItem[];
  summary: string;
}

export interface FieldResult {
  instructions: string[];
  check_items: string[];
  observations: string[];
  tags: FieldMetadata;
}

export type StructureResult = MeetingResult | FieldResult;

/** 오디오 파일을 서버에 업로드하여 STT 텍스트를 받습니다. */
export async function transcribeAudio(blob: Blob, filename: string): Promise<string> {
  const form = new FormData();
  form.append("file", blob, filename);

  const res = await fetch(`${BASE}/transcribe`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `transcribe failed: ${res.status}`);
  }
  const data = await res.json();
  return data.transcript as string;
}

/** STT 텍스트를 모드별로 구조화합니다. */
export async function structureTranscript(
  transcript: string,
  mode: Mode,
  metadata?: FieldMetadata
): Promise<StructureResult> {
  const res = await fetch(`${BASE}/structure`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ transcript, mode, metadata }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `structure failed: ${res.status}`);
  }
  const data = await res.json();
  return data.result as StructureResult;
}

/** 구조화 결과를 Word(.docx)로 다운로드합니다. */
export async function exportDocx(mode: Mode, result: StructureResult): Promise<void> {
  const res = await fetch(`${BASE}/export/docx`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode, result, format: "docx" }),
  });
  if (!res.ok) throw new Error(`export failed: ${res.status}`);

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = mode === "meeting" ? "회의록.docx" : "현장메모.docx";
  a.click();
  URL.revokeObjectURL(url);
}
