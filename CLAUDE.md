# Voice-to-Text Automation App

## Project Overview
음성 업로드 또는 실시간 녹음 → STT → 모드별 구조화 출력 PWA.

- **모드 A (회의록)**: 다수 참석자 회의 녹음 → 안건·결정사항·액션아이템·논의 요약 → Word/PDF 다운로드
- **모드 B (현장 메모)**: 혼자 말로 메모 → 업무 지시·확인 항목·현장 관찰 → 태그 저장 + 클립보드/Word

## Tech Stack
- **Backend**: FastAPI (Python 3.12), OpenAI gpt-4o-mini-transcribe, Anthropic Claude Sonnet, python-docx
- **Frontend**: React 18, TypeScript, Vite, PWA (Workbox), IndexedDB (idb)
- **Infra**: Docker, GCP Cloud Run

## Architecture
```
frontend (Vite PWA) → FastAPI backend → OpenAI STT → Claude structuring → docx/PDF response
                    ↘ IndexedDB (offline queue) → auto-upload on reconnect
```

## Directory Structure
```
voice-to-text/
├── backend/
│   ├── main.py              # FastAPI app + CORS + routes
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── routers/
│   │   ├── transcribe.py    # POST /transcribe (file upload or blob)
│   │   └── structure.py     # POST /structure (mode A or B)
│   ├── services/
│   │   ├── transcriber.py   # OpenAI Whisper STT
│   │   └── structurer.py    # Claude mode-based structuring
│   └── models/
│       └── schemas.py       # Pydantic models
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── public/manifest.json
    └── src/
        ├── App.tsx
        ├── service-worker.ts    # Offline queue + background sync
        ├── components/
        │   ├── ModeSelector.tsx
        │   ├── VoiceRecorder.tsx
        │   └── ResultView.tsx
        └── lib/
            ├── api.ts           # Backend API calls
            └── db.ts            # IndexedDB helpers (idb)
```

## Environment Variables
Backend (`.env`):
```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
ALLOWED_ORIGINS=http://localhost:5173,https://your-domain.com
```

## Key Commands
```bash
# Backend dev
cd backend && uvicorn main:app --reload --port 8000

# Frontend dev
cd frontend && npm run dev

# Docker (full stack)
docker-compose up --build

# Deploy to Cloud Run
gcloud run deploy voice-to-text-api --source backend/ --region asia-northeast3
gcloud run deploy voice-to-text-web --source frontend/ --region asia-northeast3
```

## API Endpoints
- `POST /api/transcribe` — multipart audio file → `{ transcript: string }`
- `POST /api/structure` — `{ transcript, mode, metadata? }` → structured JSON
- `POST /api/export/docx` — structured JSON → docx file download

## Notes
- STT 언어는 항상 `ko` (한국어) 고정
- 오프라인 녹음은 IndexedDB `pending-recordings` store에 Blob + metadata 저장
- Service Worker Background Sync tag: `sync-recordings`
- Cloud Run min-instances=1 권장 (cold start 방지)
