interface Option {
  value: string;
  label: string;
}

interface Props {
  label: string;
  value: string[];
  onChange: (v: string[]) => void;
  options: Option[];
  required?: boolean;
}

export function MultiSelectField({
  label,
  value,
  onChange,
  options,
  required,
}: Props) {
  const toggle = (v: string) => {
    onChange(value.includes(v) ? value.filter((x) => x !== v) : [...value, v]);
  };
  return (
    <fieldset className="space-y-1">
      <legend className="text-sm text-slate-400">
        {label}
        {required && <span className="text-red-400 ml-0.5">*</span>}
      </legend>
      <div className="flex flex-wrap gap-2">
        {options.map((o) => (
          <button
            key={o.value}
            type="button"
            onClick={() => toggle(o.value)}
            className={`px-3 py-1.5 rounded-card border text-sm transition ${
              value.includes(o.value)
                ? "bg-accent/20 border-accent text-accent"
                : "border-bg-card text-slate-300 hover:border-slate-500"
            }`}
          >
            {o.label}
          </button>
        ))}
      </div>
    </fieldset>
  );
}
