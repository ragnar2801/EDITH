import { createContext, useContext } from 'react'

import type { Schemas } from '@/api/client'

export type TransactionKind = 'lump-sum' | 'sip' | 'sell'

/** Open the global Add transaction dialog, optionally for one fund and one kind, starting in
 * one bucket. */
export type OpenAddTransaction = (
  fund?: Schemas['FundRef'],
  kind?: TransactionKind,
  bucket?: number,
) => void

export const AddTransactionContext = createContext<OpenAddTransaction | null>(null)

export function useAddTransaction(): OpenAddTransaction {
  const open = useContext(AddTransactionContext)
  if (!open) throw new Error('useAddTransaction needs an AddTransactionProvider')
  return open
}
