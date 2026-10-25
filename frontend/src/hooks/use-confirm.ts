import { createContext, useContext } from 'react'

export type ConfirmOptions = {
  title: string
  /** A short consequence, e.g. "Its saved backtests are deleted too." */
  description?: string
  action?: string
}

export type Confirm = (options: ConfirmOptions) => Promise<boolean>

export const ConfirmContext = createContext<Confirm | null>(null)

/** Ask before something destructive: `if (await confirm({ title: 'Delete X?' })) …` (D-060). */
export function useConfirm(): Confirm {
  const confirm = useContext(ConfirmContext)
  if (!confirm) throw new Error('useConfirm needs a ConfirmProvider')
  return confirm
}
