/**
 * ResultView — 모드별 구조화 결과 표시 + Word 다운로드 + 클립보드 복사(모드 B).
 */

import { useState } from "react";
import type { Mode, MeetingResult, FieldResult, StructureResult } from "../lib/api";
import { exportDocx } from "../lib/api";

interface Props {
  mode: Mode;
  result: StructureResult;
}

function isMeeting(mode: Mode, result: StructureResult): result is MeetingResult {
  return mode === "meeting";
}

// ── 모드 A — 회의록 ───────────────────────────────────────────────────────────
function MeetingView({ result }: { result: MeetingResult }) {
  return (
    <div className="result-section">
      <Section title="📌 안건">
        <BulletList items={result.agenda} />
      </Section>
      <Section title="✅ 결정사항">
        <BulletList items={result.decisions} />
      </Section>
      <Section title="🎯 액션아이템">
        <table className="result-table">
          <thead>
            <tr>
              <th>업무 내용</th>
              <th>담당자</th>
              <th>기한</th>
            </tr>
          </thead>
          <tbody>
            {result.action_items.map((ai, i) => (
              <tr key={i}>
                <td>{ai.task}</td>
                <td>{ai.assignee ?? "-"}</td>
                <td>{ai.due_date ?? "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Section>
      <Section title="📝 논의 요약">
        <p className="result-summary">{result.summary}</p>
      </Section>
    </div>
  );
}

// ── 모드 B — 현장 메모 ────────────────────────────────────────────────────────
function FieldView({ result }: { result: FieldResult }) {
  const [copied, setCopied] = useState(false);

  const plainText = [
    "【업무 지시사항】",
    ...result.instructions.map((s) => `• ${s}`),
    "",
    "【확인 필요 항목】",
    ...result.check_items.map((s) => `• ${s}`),
    "",
    "【현장 관찰 메모】",
    ...result.observations.map((s) => `• ${s}`),
  ].join("\n");

  const handleCopy = async () => {
    await navigator.clipboard.writeText(plainText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="result-section">
      {/* 태그 */}
      {result.tags && (
        <div className="result-tags">
          {result.tags.project_name && <Tag label="프로젝트" value={result.tags.project_name} />}
          {result.tags.location && <Tag label="위치" value={result.tags.location} />}
          {result.tags.record_date && <Tag label="날짜" value={result.tags.record_date} />}
        </div>
      )}
      <Section title="📋 업무 지시사항">
        <BulletList items={result.instructions} />
      </Section>
      <Section title="🔍 확인 필요 항목">
        <BulletList items={result.check_items} />
      </Section>
      <Section title="👁 현장 관찰 메모">
        <BulletList items={result.observations} />
      </Section>
      <button type="button" className="btn btn--secondary" onClick={handleCopy}>
        {copied ? "✅ 복사됨" : "📋 클립보드 복사"}
      </button>
    </div>
  );
}

// ── 공통 컴포넌트 ────────────────────────────────────────────────────────────
function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="result-block">
      <h3 className="result-block__title">{title}</h3>
      {children}
    </div>
  );
}

function BulletList({ items }: { items: string[] }) {
  if (!items.length) return <p className="result-empty">항목 없음</p>;
  return (
    <ul className="result-list">
      {items.map((item, i) => (
        <li key={i}>{item}</li>
      ))}
    </ul>
  );
}

function Tag({ label, value }: { label: string; value: string }) {
  return (
    <span className="result-tag">
      <span className="result-tag__label">{label}</span>
      <span className="result-tag__value">{value}</span>
    </span>
  );
}

// ── 메인 컴포넌트 ────────────────────────────────────────────────────────────
export function ResultView({ mode, result }: Props) {
  const [exporting, setExporting] = useState(false);

  const handleExport = async () => {
    setExporting(true);
    try {
      await exportDocx(mode, result);
    } catch (err) {
      alert(err instanceof Error ? err.message : "다운로드 실패");
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="result-view">
      <div className="result-view__header">
        <h2>{mode === "meeting" ? "🗓️ 회의록" : "📋 현장 메모"}</h2>
        <button
          type="button"
          className="btn btn--primary"
          onClick={handleExport}
          disabled={exporting}
        >
          {exporting ? "⏳ 생성 중…" : "📄 Word 다운로드"}
        </button>
      </div>

      {isMeeting(mode, result) ? (
        <MeetingView result={result} />
      ) : (
        <FieldView result={result as FieldResult} />
      )}
    </div>
  );
}
