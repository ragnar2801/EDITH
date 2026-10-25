import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

export type Tone = 'positive' | 'negative'

type Props = {
  label: string
  value: ReactNode
  hint?: ReactNode
  tone?: Tone
}

/** One headline figure: a label above a value. The value is always text from the API. */
export function Stat({ label, value, hint, tone }: Props) {
  return (
    <div className="bg-card flex min-w-0 flex-col gap-0.5 rounded-lg border px-3 py-2.5">
      <dt className="text-muted-foreground text-xs">{label}</dt>
      <dd
        className={cn(
          'truncate text-lg font-semibold tabular-nums',
          tone === 'positive' && 'text-positive',
          tone === 'negative' && 'text-destructive',
        )}
      >
        {value}
      </dd>
      {hint && <dd className="text-muted-foreground truncate text-xs">{hint}</dd>}
    </div>
  )
}

export function StatGrid({ children }: { children: ReactNode }) {
  return <dl className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">{children}</dl>
}
