import { useId, type ReactNode } from 'react'

import { InfoTip } from '@/components/InfoTip'
import { cn } from '@/lib/utils'

type Props = {
  label: string
  /** One sentence for the ⓘ next to the label. */
  info?: ReactNode
  error?: string
  size?: 'default' | 'sm'
  className?: string
  /** Gets the id to put on the control. */
  children: (id: string) => ReactNode
}

/** A label (with an optional ⓘ) above one control. No hint line: text below the control is
 * for errors only. */
export function Field({ label, info, error, size = 'default', className, children }: Props) {
  const id = useId()
  return (
    <div className={cn('flex min-w-0 flex-col', size === 'sm' ? 'gap-1' : 'gap-1.5', className)}>
      <span className="flex items-center gap-1.5">
        <label
          htmlFor={id}
          className={
            size === 'sm' ? 'text-muted-foreground text-xs font-medium' : 'text-sm font-medium'
          }
        >
          {label}
        </label>
        {info && <InfoTip label={label}>{info}</InfoTip>}
      </span>
      {children(id)}
      {error && <p className="text-destructive text-xs">{error}</p>}
    </div>
  )
}

/** A request failed: the API's problem detail, announced. */
export function ErrorText({ error }: { error: Error | null | undefined }) {
  if (!error) return null
  return (
    <p role="alert" className="text-destructive text-sm">
      {error.message}
    </p>
  )
}
