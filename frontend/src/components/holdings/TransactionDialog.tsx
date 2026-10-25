import type { Holding } from '@/api/queries'
import { DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import type { Lot, Sip } from '@/lib/holdings'

import { LotEditForm, LumpSumForm, SellForm, SipForm } from './TransactionForms'

export type TransactionMode =
  { kind: 'lump-sum' } | { kind: 'sip'; sip?: Sip } | { kind: 'sell' } | { kind: 'lot'; lot: Lot }

function title(mode: TransactionMode): string {
  switch (mode.kind) {
    case 'lump-sum':
      return 'Add lump sum'
    case 'sip':
      return mode.sip ? 'Edit SIP' : 'Start a SIP'
    case 'sell':
      return 'Sell units'
    case 'lot':
      return mode.lot.kind === 'sip' ? 'Edit SIP instalment' : 'Edit purchase'
  }
}

/** The content of a transaction dialog for one fund; put it inside a <Dialog>. */
export function TransactionDialog({
  holding,
  mode,
  onDone,
}: {
  holding: Holding
  mode: TransactionMode
  onDone: () => void
}) {
  return (
    <DialogContent>
      <DialogHeader>
        <DialogTitle>{title(mode)}</DialogTitle>
        <DialogDescription>{holding.fund.name}</DialogDescription>
      </DialogHeader>
      {mode.kind === 'lump-sum' && <LumpSumForm holding={holding} onDone={onDone} />}
      {mode.kind === 'sip' && <SipForm holding={holding} sip={mode.sip} onDone={onDone} />}
      {mode.kind === 'sell' && <SellForm holding={holding} onDone={onDone} />}
      {mode.kind === 'lot' && <LotEditForm holding={holding} lot={mode.lot} onDone={onDone} />}
    </DialogContent>
  )
}
