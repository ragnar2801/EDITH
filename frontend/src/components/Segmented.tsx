import { cn } from '@/lib/utils'

/** A row of mutually exclusive choices (a radio group that looks like tabs). */
export function Segmented<T extends string>({
  label,
  value,
  options,
  onChange,
  disabled = [],
}: {
  label: string
  value: T
  options: Record<T, string>
  onChange: (value: T) => void
  disabled?: T[]
}) {
  return (
    <div role="radiogroup" aria-label={label} className="bg-muted flex rounded-md p-0.5">
      {(Object.keys(options) as T[]).map((key) => (
        <button
          key={key}
          type="button"
          role="radio"
          aria-checked={value === key}
          disabled={disabled.includes(key)}
          onClick={() => onChange(key)}
          className={cn(
            'flex-1 rounded px-1.5 py-1 text-sm whitespace-nowrap disabled:opacity-50',
            value === key ? 'bg-background font-medium shadow-sm' : 'text-muted-foreground',
          )}
        >
          {options[key]}
        </button>
      ))}
    </div>
  )
}
