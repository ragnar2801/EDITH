import { ArrowLeft } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router'

type Props = {
  title: ReactNode
  /** A small line under the title: identity, not explanation (e.g. "Direct · Growth"). */
  meta?: ReactNode
  back?: { to: string; label: string }
  actions?: ReactNode
}

/** Every page starts with this: title and its actions, nothing to read (D-060). */
export function PageHeader({ title, meta, back, actions }: Props) {
  return (
    <header className="flex flex-col gap-1">
      {back && (
        <Link
          to={back.to}
          className="text-muted-foreground hover:text-foreground flex w-fit items-center gap-1 text-sm"
        >
          <ArrowLeft className="size-3.5" aria-hidden />
          {back.label}
        </Link>
      )}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 flex-col gap-1">
          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          {meta && (
            <div className="text-muted-foreground flex flex-wrap items-center gap-2 text-sm">
              {meta}
            </div>
          )}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
    </header>
  )
}
