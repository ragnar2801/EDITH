import type { MouseEvent, ReactNode } from 'react'
import { useNavigate } from 'react-router'

import { cn } from '@/lib/utils'

/** The one table style (D-060): bordered, muted header, figures right-aligned and tabular. */
export function Table({
  label,
  className,
  children,
}: {
  label: string
  className?: string
  children: ReactNode
}) {
  return (
    <div className={cn('overflow-x-auto rounded-lg border', className)}>
      <table className="w-full text-sm" aria-label={label}>
        {children}
      </table>
    </div>
  )
}

export function THead({ children }: { children: ReactNode }) {
  return (
    <thead className="bg-muted/50 text-muted-foreground text-left text-xs">
      <tr>{children}</tr>
    </thead>
  )
}

export function Th({
  numeric,
  className,
  children,
}: {
  numeric?: boolean
  className?: string
  children?: ReactNode
}) {
  return (
    <th
      className={cn('px-3 py-2 font-medium whitespace-nowrap', numeric && 'text-right', className)}
    >
      {children ?? <span className="sr-only">Actions</span>}
    </th>
  )
}

export function TBody({ children }: { children: ReactNode }) {
  return <tbody className="divide-y">{children}</tbody>
}

export function TFoot({ children }: { children: ReactNode }) {
  return (
    <tfoot className="border-t text-xs">
      <tr>{children}</tr>
    </tfoot>
  )
}

/** A row; with `to`, a click anywhere on it (outside its buttons and links) opens that page. */
export function Tr({
  to,
  className,
  children,
}: {
  to?: string
  className?: string
  children: ReactNode
}) {
  const navigate = useNavigate()
  function open(event: MouseEvent<HTMLTableRowElement>) {
    const target = event.target as HTMLElement
    // Clicks inside portals (menus, dialogs) bubble here through React too: ignore them.
    if (!to || !event.currentTarget.contains(target)) return
    if (target.closest('a, button, input, select, [role="menuitem"]')) return
    navigate(to)
  }
  return (
    <tr className={cn(to && 'hover:bg-muted/40 cursor-pointer', className)} onClick={open}>
      {children}
    </tr>
  )
}

export function Td({
  numeric,
  className,
  colSpan,
  children,
}: {
  numeric?: boolean
  className?: string
  colSpan?: number
  children?: ReactNode
}) {
  return (
    <td
      colSpan={colSpan}
      className={cn('px-3 py-2', numeric && 'text-right tabular-nums whitespace-nowrap', className)}
    >
      {children}
    </td>
  )
}
