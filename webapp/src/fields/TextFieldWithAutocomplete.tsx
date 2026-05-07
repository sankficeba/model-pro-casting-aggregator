import { useState } from "react";
import { useFieldSuggestions } from "../contexts/SuggestionsContext";

interface Props {
  field: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: "text" | "email" | "tel" | "url";
  required?: boolean;
}

export function TextFieldWithAutocomplete({
  field,
  label,
  value,
  onChange,
  placeholder,
  type = "text",
  required,
}: Props) {
  const suggestions = useFieldSuggestions(field).filter(
    (s): s is string => typeof s === "string",
  );
  const [focused, setFocused] = useState(false);
  const filtered = suggestions
    .filter((s) => !value || s.toLowerCase().includes(value.toLowerCase()))
    .slice(0, 5);

  return (
    <label className="block space-y-1">
      <span className="text-sm text-slate-400">
        {label}
        {required && <span className="text-red-400 ml-0.5">*</span>}
      </span>
      <div className="relative">
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setTimeout(() => setFocused(false), 150)}
          placeholder={placeholder}
          className="w-full bg-bg-card rounded-card px-3 py-2 outline-none focus:ring-1 ring-accent"
        />
        {focused &&
          filtered.length > 0 &&
          filtered.some((s) => s !== value) && (
            <ul className="absolute z-10 w-full bg-bg-card border border-bg rounded-card mt-1 shadow-lg overflow-hidden">
              {filtered.map((s) => (
                <li
                  key={s}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    onChange(s);
                  }}
                  className="px-3 py-2 hover:bg-accent/20 cursor-pointer text-sm"
                >
                  {s}
                </li>
              ))}
            </ul>
          )}
      </div>
    </label>
  );
}
