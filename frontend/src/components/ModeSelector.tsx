import type { Mode } from "../lib/api";

interface Props {
  value: Mode;
  onChange: (mode: Mode) => void;
}

const modes: { id: Mode; label: string; description: string; icon: string }[] = [
  {
    id: "meeting",
    label: "회의록",
    description: "다수 참석자 회의 녹음 → 안건·결정사항·액션아이템·요약",
    icon: "🗓️",
  },
  {
    id: "field",
    label: "현장 메모",
    description: "현장에서 혼자 말로 메모 → 지시사항·확인항목·관찰 메모",
    icon: "📋",
  },
];

export function ModeSelector({ value, onChange }: Props) {
  return (
    <div className="mode-selector">
      <p className="mode-selector__label">모드 선택</p>
      <div className="mode-selector__cards">
        {modes.map((m) => (
          <button
            key={m.id}
            type="button"
            className={`mode-card ${value === m.id ? "mode-card--active" : ""}`}
            onClick={() => onChange(m.id)}
            aria-pressed={value === m.id}
          >
            <span className="mode-card__icon">{m.icon}</span>
            <span className="mode-card__name">{m.label}</span>
            <span className="mode-card__desc">{m.description}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
