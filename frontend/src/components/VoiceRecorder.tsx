/**
 * VoiceRecorder — 파일 업로드 + MediaRecorder 실시간 녹음.
 * 오프라인 시 IndexedDB에 저장하고 onOfflineSave 콜백을 호출합니다.
 */

import { useRef, useState, useCallback } from "react";
import type { Mode, FieldMetadata } from "../lib/api";
import { savePending } from "../lib/db";

type RecordingState = "idle" | "recording" | "processing";

interface Props {
  mode: Mode;
  metadata?: FieldMetadata;
  onResult: (transcript: string) => void;
  onError: (message: string) => void;
  onOfflineSave?: () => void;
}

async function sendToServer(blob: Blob, filename: string): Promise<string> {
  const { transcribeAudio } = await import("../lib/api");
  return transcribeAudio(blob, filename);
}

export function VoiceRecorder({ mode, metadata, onResult, onError, onOfflineSave }: Props) {
  const [state, setState] = useState<RecordingState>("idle");
  const [elapsed, setElapsed] = useState(0);

  const mediaRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── 파일 업로드 ──────────────────────────────
  const handleFileChange = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      e.target.value = "";

      setState("processing");
      try {
        if (!navigator.onLine) {
          await savePending({ blob: file, filename: file.name, mode, metadata, createdAt: Date.now() });
          onOfflineSave?.();
          return;
        }
        const text = await sendToServer(file, file.name);
        onResult(text);
      } catch (err) {
        onError(err instanceof Error ? err.message : "업로드 오류");
      } finally {
        setState("idle");
      }
    },
    [mode, metadata, onResult, onError, onOfflineSave]
  );

  // ── 실시간 녹음 시작 ─────────────────────────
  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream, { mimeType: "audio/webm;codecs=opus" });
      chunksRef.current = [];

      mr.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mr.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        clearInterval(timerRef.current!);

        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        setState("processing");

        try {
          if (!navigator.onLine) {
            await savePending({ blob, filename: "recording.webm", mode, metadata, createdAt: Date.now() });
            onOfflineSave?.();
            return;
          }
          const text = await sendToServer(blob, "recording.webm");
          onResult(text);
        } catch (err) {
          onError(err instanceof Error ? err.message : "녹음 처리 오류");
        } finally {
          setState("idle");
          setElapsed(0);
        }
      };

      mr.start(1000);
      mediaRef.current = mr;
      setState("recording");
      setElapsed(0);
      timerRef.current = setInterval(() => setElapsed((s) => s + 1), 1000);
    } catch {
      onError("마이크 권한이 필요합니다.");
    }
  }, [mode, metadata, onResult, onError, onOfflineSave]);

  const stopRecording = useCallback(() => {
    mediaRef.current?.stop();
    mediaRef.current = null;
  }, []);

  const formatTime = (sec: number) =>
    `${String(Math.floor(sec / 60)).padStart(2, "0")}:${String(sec % 60).padStart(2, "0")}`;

  return (
    <div className="voice-recorder">
      {/* 파일 업로드 */}
      <div className="voice-recorder__upload">
        <label className="btn btn--secondary" htmlFor="audio-upload">
          📁 파일 업로드
          <input
            id="audio-upload"
            type="file"
            accept=".mp3,.m4a,.wav,.webm"
            style={{ display: "none" }}
            onChange={handleFileChange}
            disabled={state !== "idle"}
          />
        </label>
        <span className="voice-recorder__hint">mp3, m4a, wav</span>
      </div>

      {/* 실시간 녹음 */}
      <div className="voice-recorder__record">
        {state === "idle" && (
          <button type="button" className="btn btn--primary btn--lg" onClick={startRecording}>
            🎙️ 녹음 시작
          </button>
        )}
        {state === "recording" && (
          <button type="button" className="btn btn--danger btn--lg" onClick={stopRecording}>
            ⏹ 녹음 중지 · {formatTime(elapsed)}
          </button>
        )}
        {state === "processing" && (
          <button type="button" className="btn btn--primary btn--lg" disabled>
            ⏳ 변환 중…
          </button>
        )}
      </div>

      {!navigator.onLine && (
        <p className="voice-recorder__offline-badge">오프라인 — 녹음은 로컬에 저장됩니다</p>
      )}
    </div>
  );
}
