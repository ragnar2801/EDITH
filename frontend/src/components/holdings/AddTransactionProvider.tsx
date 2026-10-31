import { useCallback, useState, type ReactNode } from 'react'

import type { Schemas } from '@/api/client'
import { useHolding } from '@/api/queries'
import { ErrorText } from '@/components/Field'
import { InstrumentSearch } from '@/components/InstrumentSearch'
import { Loading } from '@/components/Loading'
import { Segmented } from '@/components/Segmented'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  AddTransactionContext,
  type OpenAddTransaction,
  type TransactionKind,
} from '@/hooks/use-add-transaction'
import { hasUnits } from '@/lib/holdings'
import { planLabel } from '@/lib/instruments'

import { LumpSumForm, SellForm, SipForm } from './TransactionForms'

const KIND_LABELS: Record<TransactionKind, string> = {
  'lump-sum': 'Lump sum',
  sip: 'SIP',
  sell: 'Sell',
}

type State = { fund: Schemas['FundRef'] | null; kind: TransactionKind; bucket?: number } | null

/** One Add transaction dialog for the whole app: pick a fund, a kind, fill in, save. */
export function AddTransactionProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<State>(null)
  const open = useCallback<OpenAddTransaction>(
    (fund, kind = 'lump-sum', bucket) => setState({ fund: fund ?? null, kind, bucket }),
    [],
  )
  const close = () => setState(null)

  return (
    <AddTransactionContext.Provider value={open}>
      {children}
      <Dialog open={state !== null} onOpenChange={(next) => !next && close()}>
        {state && (
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add transaction</DialogTitle>
              <DialogDescription className="sr-only">
                A lump sum, a SIP or a sale in one fund
              </DialogDescription>
            </DialogHeader>
            {state.fund ? (
              <FundTransaction
                // A new fund starts a fresh form.
                key={state.fund.id}
                fund={state.fund}
                kind={state.kind}
                bucket={state.bucket}
                onKind={(kind) => setState({ ...state, kind })}
                onChangeFund={() => setState({ ...state, fund: null })}
                onDone={close}
              />
            ) : (
              <InstrumentSearch
                autoFocus
                kind="mutual_fund"
                label="Fund"
                placeholder="Search funds"
                onSelect={(fund) => setState({ ...state, fund })}
              />
            )}
          </DialogContent>
        )}
      </Dialog>
    </AddTransactionContext.Provider>
  )
}

function FundTransaction({
  fund,
  kind,
  bucket,
  onKind,
  onChangeFund,
  onDone,
}: {
  fund: Schemas['FundRef']
  kind: TransactionKind
  bucket?: number
  onKind: (kind: TransactionKind) => void
  onChangeFund: () => void
  onDone: () => void
}) {
  const holding = useHolding(fund.id)
  const canSell = holding.data?.lots.some(hasUnits) ?? false

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-3 rounded-md border px-3 py-2">
        <span className="flex min-w-0 flex-col">
          <span className="truncate text-sm font-medium">{fund.name}</span>
          {planLabel(fund) && (
            <span className="text-muted-foreground text-xs">{planLabel(fund)}</span>
          )}
        </span>
        <Button type="button" variant="ghost" size="sm" className="ml-auto" onClick={onChangeFund}>
          Change
        </Button>
      </div>
      <Segmented
        label="Type"
        value={kind === 'sell' && holding.isSuccess && !canSell ? 'lump-sum' : kind}
        options={KIND_LABELS}
        disabled={canSell ? [] : ['sell']}
        onChange={onKind}
      />
      {holding.isPending && <Loading rows={2} />}
      <ErrorText error={holding.error} />
      {holding.isSuccess &&
        (kind === 'sip' ? (
          <SipForm holding={holding.data} bucket={bucket} onDone={onDone} />
        ) : kind === 'sell' && canSell ? (
          <SellForm holding={holding.data} onDone={onDone} />
        ) : (
          <LumpSumForm holding={holding.data} bucket={bucket} onDone={onDone} />
        ))}
    </div>
  )
}
