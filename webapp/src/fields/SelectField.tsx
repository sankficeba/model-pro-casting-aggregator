interface Option {
  value: string;
  label: string;
}

interface Props {
  label: string;
  value: string | null;
  onChange: (v: string | null) => void;
  options: Option[];
  required?: boolean;
}

export function SelectField({
  label,
  value,
  onChange,
  options,
  required,
}: Props) {
  return (
    <label className="block space-y-1">
      <span className="text-sm text-slate-400">
        {label}
        {required && <span className="text-red-400 ml-0.5">*</span>}
      </span>
      <select
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value || null)}
        className="w-full bg-bg-card rounded-card px-3 py-2 outline-none focus:ring-1 ring-accent"
      >
        <option value="">—</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}
