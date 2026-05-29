import { useState, useEffect } from "react";
import { ModeSelector } from "./components/ModeSelector";
import { VoiceRecorder } from "./components/VoiceRecorder";
import { ResultView } from "./components/ResultView";
import { structureTranscript } from "./lib/api";
import { countPending } from "./lib/db";
import type { Mode, StructureResult, FieldMetadata } from "./lib/api";

type Step = "input" | "processing" | "result";

export default function App() {
  const [mode, setMode] = useState<Mode>("meeting");
  const [step, setStep] = useState<Step>("input");
  const [transcript, setTranscript] = useState("");
  const [result, setResult] = useState<StructureResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pendingCount, setPendingCount] = useState(0);

  // 현장 메모 메타데이터 (모드 B)
  const [metadata, setMetadata] = useState<FieldMetadata>({});

  useEffect(() => {
    countPending().then(setPendingCount);
  }, []);

  // SW에서 오프라인 sync 완료 메시지 수신
  useEffect(() => {
    const handler = (e: MessageEvent) => {
      if (e.data?.type === "SYNC_RESULT") {
        setResult(e.data.payload.result);
        setStep("result");
        countPending().then(setPendingCount);
      }
    };
    navigator.serviceWorker?.addEventListener("message", handler);
    return () => navigator.serviceWorker?.removeEventListener("message", handler);
  }, []);

  const handleTranscript = async (text: string) => {
    setTranscript(text);
    setStep("processing");
    setError(null);
    try {
      const structured = await structureTranscript(text, mode, mode === "field" ? metadata : undefined);
      setResult(structured);
      setStep("result");
    } catch (err) {
      setError(err instanceof Error ? err.message : "오류가 발생했습니다.");
      setStep("input");
    }
  };

  const handleReset = () => {
    setStep("input");
    setTranscript("");
    setResult(null);
    setError(null);
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>🎙️ 음성 기록 자동화기</h1>
        {pendingCount > 0 && (
          <span className="badge badge--warn">오프라인 대기 {pendingCount}건</span>
        )}
      </header>

      <main className="app-main">
        {step === "input" && (
          <>
            <ModeSelector value={mode} onChange={(m) => { setMode(m); setError(null); }} />

            {/* 모드 B 메타데이터 입력 */}
            {mode === "field" && (
              <div className="metadata-form">
                <input
                  placeholder="프로젝트명"
                  value={metadata.project_name ?? ""}
                  onChange={(e) => setMetadata((m) => ({ ...m, project_name: e.target.value }))}
                />
                <input
                  placeholder="위치"
                  value={metadata.location ?? ""}
                  onChange={(e) => setMetadata((m) => ({ ...m, location: e.target.value }))}
                />
                <input
                  type="date"
                  value={metadata.record_date ?? ""}
                  onChange={(e) => setMetadata((m) => ({ ...m, record_date: e.target.value }))}
                />
              </div>
            )}

            <VoiceRecorder
              mode={mode}
              metadata={mode === "field" ? metadata : undefined}
              onResult={handleTranscript}
              onError={setError}
              onOfflineSave={() => countPending().then(setPendingCount)}
            />

            {error && <p className="error-msg">⚠️ {error}</p>}
          </>
        )}

        {step === "processing" && (
          <div className="processing">
            <div className="spinner" />
            <p>Claude가 구조화 중입니다…</p>
            {transcript && (
              <details>
                <summary>원문 보기</summary>
                <pre className="transcript-preview">{transcript}</pre>
              </details>
            )}
          </div>
        )}

        {step === "result" && result && (
          <>
            <ResultView mode={mode} result={result} />
            <button type="button" className="btn btn--secondary" onClick={handleReset}>
              ← 새 녹음
            </button>
          </>
        )}
      </main>
    </div>
  );
}
