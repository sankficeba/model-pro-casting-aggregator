/* Переиспользуемые UI-компоненты под dark theme со скринов. */
import { ReactNode } from "react";
import type { RefItem } from "../types";

// ========== Field wrapper ==========

export function Field({
  label,
  required,
  hint,
  children,
}: {
  label: string;
  required?: boolean;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label className="text-sm text-slate-300">
        {label}
        {required && <span className="text-accent ml-0.5">*</span>}
        {hint && <span className="text-xs text-slate-500 ml-1">({hint})</span>}
      </label>
      {children}
    </div>
  );
}

// ========== TextInput ==========

export function TextInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={
        "w-full px-3.5 py-3 rounded-xl bg-bg-card border border-bg-card " +
        "focus:border-accent focus:ring-1 focus:ring-accent transition " +
        "placeholder:text-slate-600 " +
        (props.className ?? "")
      }
    />
  );
}

// ========== Number range ==========

export function RangeInput({
  min,
  max,
  onChange,
  placeholderMin,
  placeholderMax,
}: {
  min: number | null | undefined;
  max: number | null | undefined;
  onChange: (next: { min: number | null; max: number | null }) => void;
  placeholderMin?: string;
  placeholderMax?: string;
}) {
  return (
    <div className="grid grid-cols-[1fr_auto_1fr] gap-2 items-center">
      <TextInput
        type="number"
        value={min ?? ""}
        placeholder={placeholderMin ?? "от"}
        onChange={(e) =>
          onChange({
            min: e.target.value === "" ? null : Number(e.target.value),
            max: max ?? null,
          })
        }
      />
      <span className="text-slate-500">—</span>
      <TextInput
        type="number"
        value={max ?? ""}
        placeholder={placeholderMax ?? "до"}
        onChange={(e) =>
          onChange({
            min: min ?? null,
            max: e.target.value === "" ? null : Number(e.target.value),
          })
        }
      />
    </div>
  );
}

// ========== Toggle ==========

export function Toggle({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label?: string;
}) {
  const inner = (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={
        "relative w-11 h-6 rounded-full transition-colors " +
        (checked ? "bg-accent" : "bg-bg-card border border-slate-700")
      }
    >
      <span
        className={
          "absolute top-0.5 w-5 h-5 rounded-full bg-white transition-transform " +
          (checked ? "translate-x-5" : "translate-x-0.5")
        }
      />
    </button>
  );
  if (!label) return inner;
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-slate-200">{label}</span>
      {inner}
    </div>
  );
}

// ========== Two-button radio (большой Yes/No) ==========

export function PairButtons<T extends string>({
  value,
  onChange,
  options,
}: {
  value: T | null | undefined;
  onChange: (v: T) => void;
  options: { value: T; label: string }[];
}) {
  return (
    <div className="grid grid-cols-2 gap-2">
      {options.map((opt) => {
        const active = value === opt.value;
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            className={
              "py-3 rounded-xl text-sm font-medium border transition " +
              (active
                ? "bg-bg-card border-accent text-accent"
                : "bg-bg-card border-bg-card text-slate-300 hover:border-slate-700")
            }
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

// ========== Single-select dropdown ==========

export function SelectInput({
  value,
  onChange,
  options,
  placeholder,
  allowEmpty = true,
}: {
  value: string | null | undefined;
  onChange: (v: string | null) => void;
  options: RefItem[];
  placeholder?: string;
  allowEmpty?: boolean;
}) {
  return (
    <select
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value || null)}
      className="w-full px-3.5 py-3 rounded-xl bg-bg-card border border-bg-card focus:border-accent focus:ring-1 focus:ring-accent transition appearance-none"
      style={{
        backgroundImage:
          "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'><path fill='%2394a3b8' d='M6 8L0 0h12z'/></svg>\")",
        backgroundRepeat: "no-repeat",
        backgroundPosition: "right 14px center",
      }}
    >
      {allowEmpty && (
        <option value="" className="text-slate-500">
          {placeholder ?? "—"}
        </option>
      )}
      {options.map((opt) => (
        <option key={opt.code} value={opt.code}>
          {opt.label}
        </option>
      ))}
    </select>
  );
}

// ========== Multi-select chips ==========

export function ChipGroup({
  value,
  onChange,
  options,
}: {
  value: string[];
  onChange: (next: string[]) => void;
  options: RefItem[];
}) {
  const toggle = (code: string) => {
    if (value.includes(code)) onChange(value.filter((c) => c !== code));
    else onChange([...value, code]);
  };
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((opt) => {
        const active = value.includes(opt.code);
        return (
          <button
            key={opt.code}
            type="button"
            onClick={() => toggle(opt.code)}
            className={
              "px-3.5 py-1.5 rounded-chip text-sm transition border " +
              (active
                ? "bg-bg-card border-accent text-accent"
                : "bg-bg-card border-slate-700 text-slate-300 hover:border-slate-500")
            }
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

// ========== Section card ==========

export function Section({
  title,
  emoji,
  children,
}: {
  title: string;
  emoji?: string;
  children: ReactNode;
}) {
  return (
    <div className="rounded-card bg-bg-surface p-4 space-y-3">
      <div className="flex items-center gap-2 text-sm font-medium">
        {emoji && <span>{emoji}</span>}
        <span>{title}</span>
      </div>
      {children}
    </div>
  );
}

// ========== Progress bar ==========

export function ProgressBar({ pct }: { pct: number }) {
  return (
    <div className="w-full h-1.5 bg-bg-card rounded-full overflow-hidden">
      <div
        className="h-full bg-accent rounded-full transition-all"
        style={{ width: `${Math.max(0, Math.min(100, pct))}%` }}
      />
    </div>
  );
}

// ========== Big primary button ==========

export function PrimaryButton({
  children,
  onClick,
  disabled,
  type = "button",
}: {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  type?: "button" | "submit";
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={
        "w-full py-3.5 rounded-xl text-sm font-medium transition " +
        (disabled
          ? "bg-slate-700 text-slate-500 cursor-not-allowed"
          : "bg-primary text-white hover:bg-primary-hover")
      }
    >
      {children}
    </button>
  );
}
