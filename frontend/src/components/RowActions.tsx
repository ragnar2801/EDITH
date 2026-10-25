import { MoreHorizontal, type LucideIcon } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

export type RowAction = {
  label: string
  onSelect: () => void
  icon?: LucideIcon
  destructive?: boolean
  disabled?: boolean
  hidden?: boolean
}

/** A row's actions behind one ⋯ button; destructive ones last, after a separator. */
export function RowActions({ label, actions }: { label: string; actions: RowAction[] }) {
  const shown = actions.filter((action) => !action.hidden)
  if (shown.length === 0) return null
  const safe = shown.filter((action) => !action.destructive)
  const destructive = shown.filter((action) => action.destructive)
  const item = ({
    label: text,
    onSelect,
    icon: Icon,
    destructive: danger,
    disabled,
  }: RowAction) => (
    <DropdownMenuItem
      key={text}
      variant={danger ? 'destructive' : 'default'}
      disabled={disabled}
      onSelect={onSelect}
    >
      {Icon && <Icon aria-hidden />}
      {text}
    </DropdownMenuItem>
  )
  return (
    <DropdownMenu modal={false}>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="size-8" aria-label={label}>
          <MoreHorizontal />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {safe.map(item)}
        {safe.length > 0 && destructive.length > 0 && <DropdownMenuSeparator />}
        {destructive.map(item)}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
