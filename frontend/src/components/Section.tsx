import type { ReactNode } from 'react'

/** A titled part of a page: a noun and its actions, no description (D-060). */
export function Section({
  title,
  info,
  actions,
  children,
}: {
  title: string
  info?: ReactNode
  actions?: ReactNode
  children: ReactNode
}) {
  return (
    <section className="flex flex-col gap-3" aria-label={title}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-1.5 text-base font-semibold">
          {title}
          {info}
        </h2>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
      {children}
    </section>
  )
}
