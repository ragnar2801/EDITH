import { Pencil, Receipt, SkipForward, Trash2, Undo2 } from 'lucide-react'
import { Fragment, type ReactNode } from 'react'
import { toast } from 'sonner'

import {
  useDeleteLot,
  useDeleteSale,
  useDeleteSip,
  useUpdateLot,
  type Holding,
} from '@/api/queries'
import { Table, TBody, Td, Th, THead, Tr } from '@/components/DataTable'
import { EmptyState } from '@/components/EmptyState'
import { ErrorText } from '@/components/Field'
import { RowActions } from '@/components/RowActions'
import { Section } from '@/components/Section'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useConfirm } from '@/hooks/use-confirm'
import { KIND_LABELS, type Lot, type Sip } from '@/lib/holdings'
import { formatNav, formatUnits, inr } from '@/lib/money'
import { formatDate } from '@/lib/time'

import type { TransactionMode } from './TransactionDialog'

/** A fund's SIPs, then its purchases with what was sold from each. */
export function Transactions({
  holding,
  onOpen,
  empty,
}: {
  holding: Holding
  onOpen: (mode: TransactionMode) => void
  /** The button the empty state offers. */
  empty: ReactNode
}) {
  if (holding.lots.length === 0 && holding.sips.length === 0) {
    return <EmptyState icon={Receipt} title="No transactions" action={empty} />
  }
  return (
    <div className="flex flex-col gap-8">
      {holding.sips.length > 0 && (
        <SipTable holding={holding} onEdit={(sip) => onOpen({ kind: 'sip', sip })} />
      )}
      <Purchases holding={holding} onEdit={(lot) => onOpen({ kind: 'lot', lot })} />
    </div>
  )
}

function SipTable({ holding, onEdit }: { holding: Holding; onEdit: (sip: Sip) => void }) {
  const remove = useDeleteSip(holding.fund.id)
  const confirm = useConfirm()

  async function onDelete(sip: Sip) {
    const yes = await confirm({
      title: 'Delete this SIP?',
      description: 'Its instalments are deleted too.',
    })
    if (yes) remove.mutate(sip.id, { onSuccess: () => toast.success('SIP deleted') })
  }

  return (
    <Section title="SIPs">
      <Table label="SIPs">
        <THead>
          <Th>Amount</Th>
          <Th>Day</Th>
          <Th>From</Th>
          <Th>To</Th>
          <Th numeric>Instalments</Th>
          <Th>Status</Th>
          <Th />
        </THead>
        <TBody>
          {holding.sips.map((sip) => (
            <Tr key={sip.id}>
              <Td className="font-medium tabular-nums">{inr(sip.amount)}</Td>
              <Td>{sip.day}</Td>
              <Td className="whitespace-nowrap">{formatDate(sip.start_date)}</Td>
              <Td className="whitespace-nowrap">{sip.end_date ? formatDate(sip.end_date) : '—'}</Td>
              <Td numeric>{sip.instalments}</Td>
              <Td>
                <Badge variant="outline">{sip.active ? 'Active' : 'Ended'}</Badge>
                {sip.note && <div className="text-muted-foreground text-xs">{sip.note}</div>}
              </Td>
              <Td className="w-0">
                <RowActions
                  label={`Actions for the ${inr(sip.amount)} SIP`}
                  actions={[
                    { label: 'Edit', icon: Pencil, onSelect: () => onEdit(sip) },
                    {
                      label: 'Delete',
                      icon: Trash2,
                      destructive: true,
                      onSelect: () => void onDelete(sip),
                    },
                  ]}
                />
              </Td>
            </Tr>
          ))}
        </TBody>
      </Table>
      <ErrorText error={remove.error} />
    </Section>
  )
}

function Purchases({ holding, onEdit }: { holding: Holding; onEdit: (lot: Lot) => void }) {
  const id = holding.fund.id
  const skip = useUpdateLot(id)
  const remove = useDeleteLot(id)
  const undo = useDeleteSale(id)
  const confirm = useConfirm()
  const error = skip.error ?? remove.error ?? undo.error

  async function onDelete(lot: Lot) {
    if (await confirm({ title: `Delete the ${formatDate(lot.buy_date)} purchase?` })) {
      remove.mutate(lot.id, { onSuccess: () => toast.success('Purchase deleted') })
    }
  }

  return (
    <Section title="Purchases">
      <ErrorText error={error} />
      {holding.lots.length === 0 ? (
        <p className="text-muted-foreground text-sm">None yet</p>
      ) : (
        <Table label="Purchases">
          <THead>
            <Th>Date</Th>
            <Th>Type</Th>
            <Th numeric>Amount</Th>
            <Th numeric>NAV</Th>
            <Th numeric>Units</Th>
            <Th numeric>Units left</Th>
            <Th numeric>Invested left</Th>
            <Th />
          </THead>
          <TBody>
            {/* Newest first; the API sends them oldest first. */}
            {[...holding.lots].reverse().map((lot) => (
              <Fragment key={lot.id}>
                <Tr className={lot.skipped ? 'text-muted-foreground' : undefined}>
                  <Td className="whitespace-nowrap">{formatDate(lot.buy_date)}</Td>
                  <Td>
                    <span className="flex flex-wrap items-center gap-1">
                      {KIND_LABELS[lot.kind]}
                      {lot.skipped && <Badge variant="outline">Skipped</Badge>}
                      {lot.edited && !lot.skipped && <Badge variant="outline">Edited</Badge>}
                    </span>
                    {lot.note && <div className="text-muted-foreground text-xs">{lot.note}</div>}
                  </Td>
                  <Td numeric>{lot.skipped ? '—' : inr(lot.amount)}</Td>
                  <Td numeric>{lot.skipped ? '—' : formatNav(lot.nav)}</Td>
                  <Td numeric>{formatUnits(lot.units)}</Td>
                  <Td numeric>{formatUnits(lot.units_remaining)}</Td>
                  <Td numeric>{inr(lot.cost_remaining)}</Td>
                  <Td className="w-0">
                    <RowActions
                      label={`Actions for the ${formatDate(lot.buy_date)} purchase`}
                      actions={[
                        {
                          label: lot.skipped ? 'Unskip' : 'Edit',
                          icon: Pencil,
                          onSelect: () => onEdit(lot),
                        },
                        {
                          label: 'Skip',
                          icon: SkipForward,
                          hidden: lot.kind !== 'sip' || lot.skipped || lot.sales.length > 0,
                          disabled: skip.isPending,
                          onSelect: () =>
                            skip.mutate({
                              id: lot.id,
                              body: {
                                buy_date: lot.buy_date,
                                amount: lot.amount,
                                note: lot.note,
                                skipped: true,
                              },
                            }),
                        },
                        {
                          label: 'Delete',
                          icon: Trash2,
                          destructive: true,
                          hidden: lot.kind !== 'lump_sum' || lot.sales.length > 0,
                          onSelect: () => void onDelete(lot),
                        },
                      ]}
                    />
                  </Td>
                </Tr>
                {lot.sales.map((sale) => (
                  <tr key={`sale-${sale.id}`} className="bg-muted/30 text-muted-foreground text-xs">
                    <Td className="py-1.5 pl-6 whitespace-nowrap">{formatDate(sale.sale_date)}</Td>
                    <Td className="py-1.5" colSpan={2}>
                      Sold {formatUnits(sale.units)} units for {inr(sale.amount)} · realised{' '}
                      {inr(sale.realised)}
                    </Td>
                    <Td numeric className="py-1.5">
                      {formatNav(sale.nav)}
                    </Td>
                    <Td className="py-1.5" colSpan={3} />
                    <Td className="py-1.5">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-7"
                        disabled={undo.isPending}
                        aria-label={`Undo the ${formatDate(sale.sale_date)} sale of ${formatUnits(sale.units)} units`}
                        onClick={() =>
                          undo.mutate(sale.id, { onSuccess: () => toast.success('Sale undone') })
                        }
                      >
                        <Undo2 /> Undo
                      </Button>
                    </Td>
                  </tr>
                ))}
              </Fragment>
            ))}
          </TBody>
        </Table>
      )}
    </Section>
  )
}
