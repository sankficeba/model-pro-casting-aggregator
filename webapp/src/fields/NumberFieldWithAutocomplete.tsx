import { useFieldSuggestions } from "../contexts/SuggestionsContext";

interface Props {
  field: string;
  label: string;
  value: number | null;
  onChange: (v: number | null) => void;
  min?: number;
  max?: number;
  placeholder?: string;
  required?: boolean;
}

export function NumberFieldWithAutocomplete({
  field,
  label,
  value,
  onChange,
  min,
  max,
  placeholder,
  required,
}: Props) {
  const suggestions = useFieldSuggestions(field).filter(
    (s): s is number => typeof s === "number",
  );

  return (
    <label className="block space-y-1">
      <span className="text-sm text-slate-400">
        {label}
        {required && <span className="text-red-400 ml-0.5">*</span>}
      </span>
      <input
        type="text"
        inputMode="numeric"
        pattern="[0-9]*"
        value={value ?? ""}
        onChange={(e) => {
          const digits = e.target.value.replace(/\D/g, "");
          onChange(digits === "" ? null : Number(digits));
        }}
        onBlur={() => {
          if (value == null) return;
          let n = value;
          if (max !== undefined && n > max) n = max;
          if (min !== undefined && n < min) n = min;
          if (n !== value) onChange(n);
        }}
        placeholder={placeholder}
        className="w-full bg-bg-card rounded-card px-3 py-2 outline-none focus:ring-1 ring-accent"
      />
      {suggestions.length > 0 && value === null && (
        <div className="flex gap-2 mt-1">
          {suggestions.slice(0, 3).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => onChange(s)}
              className="text-xs px-2 py-1 rounded-card border border-bg-card text-slate-400 hover:border-accent hover:text-accent"
            >
              {s}
            </button>
          ))}
        </div>
      )}
    </label>
  );
}
