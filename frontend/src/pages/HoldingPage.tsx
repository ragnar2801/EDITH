import { Loader2, Plus, Repeat, Undo2 } from 'lucide-react'
import { Fragment, useId, useState, type FormEvent, type ReactNode } from 'react'
import { Link, useParams } from 'react-router'

import {
  useAddLumpSum,
  useDeleteLot,
  useDeleteSale,
  useDeleteSip,
  useHolding,
  useSaveSip,
  useSell,
  useUpdateLot,
  type Holding,
} from '@/api/queries'
import { Stat, StatGrid } from '@/components/Stat'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { hasUnits, KIND_LABELS, type Lot, type Sip } from '@/lib/holdings'
import { planLabel } from '@/lib/instruments'
import { formatNav, formatUnits, inr } from '@/lib/money'
import { formatDate, todayIst } from '@/lib/time'

type Mode =
  | { kind: 'lump-sum' }
  | { kind: 'sip'; sip?: Sip }
  | { kind: 'sell' }
  | { kind: 'lot'; lot: Lot }
  | null

export function HoldingPage() {
  const id = Number(useParams().id)
  const holding = useHolding(id)
  const [mode, setMode] = useState<Mode>(null)

  if (holding.isPending) return <p className="text-muted-foreground text-sm">Loading…</p>
  if (holding.isError) return <p className="text-destructive text-sm">{holding.error.message}</p>

  const data = holding.data
  const done = () => setMode(null)
  const plan = planLabel(data.fund)
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <div>
        <Link to="/holdings" className="text-muted-foreground text-sm hover:underline">
          ← Holdings
        </Link>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">{data.fund.name}</h1>
        <p className="text-muted-foreground mt-1 text-sm">
          AMFI {data.fund.amfi_code}
          {plan && ` · ${plan}`} ·{' '}
          <Link to={`/instruments/${data.fund.id}`} className="underline-offset-4 hover:underline">
            Fund details and NAVs
          </Link>
        </p>
      </div>

      <StatGrid>
        <Stat label="Units held" value={formatUnits(data.units)} />
        <Stat label="Cost of units held" value={inr(data.cost)} />
        <Stat label="Lots" value={data.lots.filter((lot) => !lot.skipped).length} />
        <Stat
          label="NAVs"
          value={data.coverage.last ? `to ${formatDate(data.coverage.last)}` : 'none yet'}
          hint={data.coverage.count === 0 ? 'Downloaded when you add a lump sum or SIP' : undefined}
        />
      </StatGrid>

      {!mode && (
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => setMode({ kind: 'lump-sum' })}>
            <Plus /> Add lump sum
          </Button>
          <Button variant="outline" onClick={() => setMode({ kind: 'sip' })}>
            <Repeat /> Start a SIP
          </Button>
          <Button
            variant="outline"
            disabled={!data.lots.some(hasUnits)}
            onClick={() => setMode({ kind: 'sell' })}
          >
            Sell units
          </Button>
        </div>
      )}
      {mode?.kind === 'lump-sum' && <LumpSumForm holding={data} onDone={done} />}
      {mode?.kind === 'lot' && <LotEditForm holding={data} lot={mode.lot} onDone={done} />}
      {mode?.kind === 'sip' && <SipForm holding={data} sip={mode.sip} onDone={done} />}
      {mode?.kind === 'sell' && <SellForm holding={data} onDone={done} />}

      {data.sips.length > 0 && (
        <SipList holding={data} onEdit={(sip) => setMode({ kind: 'sip', sip })} />
      )}
      <LotsTable holding={data} onEdit={(lot) => setMode({ kind: 'lot', lot })} />
    </div>
  )
}

function Field({
  label,
  hint,
  children,
}: {
  label: string
  hint?: string
  children: (id: string) => ReactNode
}) {
  const id = useId()
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      {children(id)}
      {hint && <p className="text-muted-foreground text-xs">{hint}</p>}
    </div>
  )
}

function FormCard({
  title,
  description,
  label,
  error,
  pending,
  submit,
  onSubmit,
  onCancel,
  children,
}: {
  title: string
  description: ReactNode
  label: string
  error: Error | null
  pending: boolean
  submit: string
  onSubmit: () => void
  onCancel: () => void
  children: ReactNode
}) {
  function handle(event: FormEvent) {
    event.preventDefault()
    onSubmit()
  }
  return (
    <Card className="border-primary/40">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <form aria-label={label} className="flex flex-col gap-4" onSubmit={handle}>
          {children}
          {error && (
            <p role="alert" className="text-destructive text-sm">
              {error.message}
            </p>
          )}
          <div className="flex flex-wrap justify-end gap-2">
            <Button type="button" variant="ghost" onClick={onCancel}>
              Cancel
            </Button>
            <Button type="submit" disabled={pending}>
              {pending && <Loader2 className="animate-spin" />}
              {submit}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}

type BuyDraft = { buy_date: string; amount: string; nav: string; units: string; note: string }

function BuyFields({
  draft,
  update,
}: {
  draft: BuyDraft
  update: (patch: Partial<BuyDraft>) => void
}) {
  return (
    <>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Date">
          {(id) => (
            <Input
              id={id}
              type="date"
              required
              max={todayIst()}
              value={draft.buy_date}
              onChange={(event) => update({ buy_date: event.target.value })}
            />
          )}
        </Field>
        <Field label="Amount (₹)">
          {(id) => (
            <Input
              id={id}
              inputMode="decimal"
              required
              value={draft.amount}
              onChange={(event) => update({ amount: event.target.value })}
            />
          )}
        </Field>
        <Field label="NAV (optional)" hint="Blank: the fund's NAV on that date.">
          {(id) => (
            <Input
              id={id}
              inputMode="decimal"
              value={draft.nav}
              onChange={(event) => update({ nav: event.target.value })}
            />
          )}
        </Field>
        <Field
          label="Units (optional)"
          hint="Blank: amount ÷ NAV, to 3 places. Or your statement's."
        >
          {(id) => (
            <Input
              id={id}
              inputMode="decimal"
              value={draft.units}
              onChange={(event) => update({ units: event.target.value })}
            />
          )}
        </Field>
      </div>
      <Field label="Note (optional)">
        {(id) => (
          <Input
            id={id}
            maxLength={200}
            value={draft.note}
            onChange={(event) => update({ note: event.target.value })}
          />
        )}
      </Field>
    </>
  )
}

function buyBody(draft: BuyDraft) {
  return {
    buy_date: draft.buy_date,
    amount: draft.amount.trim(),
    nav: draft.nav.trim() || null,
    units: draft.units.trim() || null,
    note: draft.note.trim() || null,
  }
}

function LumpSumForm({ holding, onDone }: { holding: Holding; onDone: () => void }) {
  const add = useAddLumpSum(holding)
  const [draft, setDraft] = useState<BuyDraft>({
    buy_date: todayIst(),
    amount: '',
    nav: '',
    units: '',
    note: '',
  })
  return (
    <FormCard
      title="Add lump sum"
      description="One buy is one lot."
      label="Lump sum"
      error={add.error}
      pending={add.isPending}
      submit="Save lump sum"
      onSubmit={() => add.mutate(buyBody(draft), { onSuccess: onDone })}
      onCancel={onDone}
    >
      <BuyFields draft={draft} update={(patch) => setDraft({ ...draft, ...patch })} />
    </FormCard>
  )
}

function LotEditForm({ holding, lot, onDone }: { holding: Holding; lot: Lot; onDone: () => void }) {
  const save = useUpdateLot(holding.fund.id)
  const [draft, setDraft] = useState<BuyDraft>({
    buy_date: lot.buy_date,
    amount: lot.amount,
    nav: lot.skipped ? '' : lot.nav,
    units: lot.skipped ? '' : lot.units,
    note: lot.note ?? '',
  })
  const instalment = lot.kind === 'sip'
  return (
    <FormCard
      title={instalment ? 'Edit SIP instalment' : 'Edit lump sum'}
      description={
        instalment
          ? 'Type the figures from your statement. Changing the SIP later keeps them.'
          : 'Units already sold from this lot stay sold.'
      }
      label="Lot"
      error={save.error}
      pending={save.isPending}
      submit="Save lot"
      onSubmit={() =>
        save.mutate(
          { id: lot.id, body: { ...buyBody(draft), skipped: false } },
          { onSuccess: onDone },
        )
      }
      onCancel={onDone}
    >
      <BuyFields draft={draft} update={(patch) => setDraft({ ...draft, ...patch })} />
    </FormCard>
  )
}

function SipForm({ holding, sip, onDone }: { holding: Holding; sip?: Sip; onDone: () => void }) {
  const save = useSaveSip(holding)
  const [draft, setDraft] = useState({
    amount: sip?.amount ?? '',
    day: String(sip?.day ?? 5),
    start_date: sip?.start_date ?? '',
    end_date: sip?.end_date ?? '',
    note: sip?.note ?? '',
  })
  const update = (patch: Partial<typeof draft>) => setDraft({ ...draft, ...patch })
  return (
    <FormCard
      title={sip ? 'Edit SIP' : 'Start a SIP'}
      description={
        sip
          ? 'Instalments are rebuilt; the ones you edited, skipped or sold from stay as they are.'
          : 'Friday adds one instalment a month on the first NAV date on or after the SIP day, and keeps adding them after every NAV sync.'
      }
      label="SIP"
      error={save.error}
      pending={save.isPending}
      submit={sip ? 'Save SIP' : 'Start SIP'}
      onSubmit={() =>
        save.mutate(
          {
            id: sip?.id,
            body: {
              amount: draft.amount.trim(),
              day: Number(draft.day),
              start_date: draft.start_date,
              end_date: draft.end_date || null,
              note: draft.note.trim() || null,
            },
          },
          { onSuccess: onDone },
        )
      }
      onCancel={onDone}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Amount each month (₹)">
          {(id) => (
            <Input
              id={id}
              inputMode="decimal"
              required
              value={draft.amount}
              onChange={(event) => update({ amount: event.target.value })}
            />
          )}
        </Field>
        <Field label="SIP day" hint="Day of the month, 1 to 28.">
          {(id) => (
            <Input
              id={id}
              type="number"
              min={1}
              max={28}
              required
              value={draft.day}
              onChange={(event) => update({ day: event.target.value })}
            />
          )}
        </Field>
        <Field label="Start date">
          {(id) => (
            <Input
              id={id}
              type="date"
              required
              max={todayIst()}
              value={draft.start_date}
              onChange={(event) => update({ start_date: event.target.value })}
            />
          )}
        </Field>
        <Field label="End date (optional)" hint="Blank: still running.">
          {(id) => (
            <Input
              id={id}
              type="date"
              value={draft.end_date}
              onChange={(event) => update({ end_date: event.target.value })}
            />
          )}
        </Field>
      </div>
      <Field label="Note (optional)">
        {(id) => (
          <Input
            id={id}
            maxLength={200}
            value={draft.note}
            onChange={(event) => update({ note: event.target.value })}
          />
        )}
      </Field>
    </FormCard>
  )
}

function SellForm({ holding, onDone }: { holding: Holding; onDone: () => void }) {
  const sell = useSell(holding.fund.id)
  const lots = holding.lots.filter(hasUnits)
  const [saleDate, setSaleDate] = useState(todayIst())
  const [nav, setNav] = useState('')
  const [units, setUnits] = useState<Record<number, string>>({})
  const picked = lots.filter((lot) => (units[lot.id] ?? '').trim())
  return (
    <FormCard
      title="Sell units"
      description="Type how many units to take from each lot you sell from. Lots left blank are untouched."
      label="Sale"
      error={sell.error}
      pending={sell.isPending}
      submit="Sell"
      onSubmit={() =>
        sell.mutate(
          {
            sale_date: saleDate,
            nav: nav.trim() || null,
            lots: picked.map((lot) => ({ lot_id: lot.id, units: units[lot.id].trim() })),
          },
          { onSuccess: onDone },
        )
      }
      onCancel={onDone}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Sale date">
          {(id) => (
            <Input
              id={id}
              type="date"
              required
              max={todayIst()}
              value={saleDate}
              onChange={(event) => setSaleDate(event.target.value)}
            />
          )}
        </Field>
        <Field label="NAV (optional)" hint="Blank: the fund's NAV on the sale date.">
          {(id) => (
            <Input
              id={id}
              inputMode="decimal"
              value={nav}
              onChange={(event) => setNav(event.target.value)}
            />
          )}
        </Field>
      </div>
      <ul className="flex flex-col divide-y rounded-md border text-sm">
        {lots.map((lot) => (
          <li key={lot.id} className="flex flex-wrap items-center gap-3 px-3 py-2">
            <span className="min-w-0">
              <span className="font-medium">{formatDate(lot.buy_date)}</span>{' '}
              <span className="text-muted-foreground">
                · {KIND_LABELS[lot.kind]} · {formatUnits(lot.units_remaining)} units left
              </span>
            </span>
            <span className="ml-auto flex items-center gap-1">
              <Input
                aria-label={`Units to sell from the ${formatDate(lot.buy_date)} lot`}
                className="w-32 text-right"
                inputMode="decimal"
                value={units[lot.id] ?? ''}
                onChange={(event) => setUnits({ ...units, [lot.id]: event.target.value })}
              />
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={() => setUnits({ ...units, [lot.id]: lot.units_remaining })}
              >
                All
              </Button>
            </span>
          </li>
        ))}
      </ul>
    </FormCard>
  )
}

function SipList({ holding, onEdit }: { holding: Holding; onEdit: (sip: Sip) => void }) {
  const remove = useDeleteSip(holding.fund.id)
  return (
    <section className="flex flex-col gap-2">
      <h2 className="text-lg font-semibold">SIPs</h2>
      <ul className="flex flex-col divide-y rounded-lg border text-sm">
        {holding.sips.map((sip) => (
          <li key={sip.id} className="flex flex-wrap items-center gap-3 px-3 py-2">
            <span className="flex flex-wrap items-center gap-2">
              <span className="font-medium tabular-nums">{inr(sip.amount)}</span>
              <span className="text-muted-foreground">
                on day {sip.day} · from {formatDate(sip.start_date)}
                {sip.end_date && ` to ${formatDate(sip.end_date)}`} · {sip.instalments}{' '}
                {sip.instalments === 1 ? 'instalment' : 'instalments'}
              </span>
              <Badge variant="outline">{sip.active ? 'Active' : 'Ended'}</Badge>
              {sip.note && <span className="text-muted-foreground">{sip.note}</span>}
            </span>
            <span className="ml-auto flex gap-1">
              <Button size="sm" variant="outline" onClick={() => onEdit(sip)}>
                Edit
              </Button>
              <Button
                size="sm"
                variant="ghost"
                disabled={remove.isPending}
                onClick={() => {
                  if (confirm('Delete this SIP and all its instalments?')) remove.mutate(sip.id)
                }}
              >
                Delete
              </Button>
            </span>
          </li>
        ))}
      </ul>
      {remove.isError && (
        <p role="alert" className="text-destructive text-sm">
          {remove.error.message}
        </p>
      )}
    </section>
  )
}

function LotsTable({ holding, onEdit }: { holding: Holding; onEdit: (lot: Lot) => void }) {
  const id = holding.fund.id
  const skip = useUpdateLot(id)
  const remove = useDeleteLot(id)
  const undo = useDeleteSale(id)
  const error = skip.error ?? remove.error ?? undo.error

  if (holding.lots.length === 0) {
    return (
      <p className="text-muted-foreground text-sm">
        No lots yet.
        {holding.sips.length > 0 && ' SIP instalments appear once Friday has NAVs for their dates.'}
      </p>
    )
  }
  return (
    <section className="flex flex-col gap-2">
      <h2 className="text-lg font-semibold">Lots</h2>
      {error && (
        <p role="alert" className="text-destructive text-sm">
          {error.message}
        </p>
      )}
      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-muted-foreground text-left text-xs">
            <tr>
              <th className="px-3 py-2 font-medium">Date</th>
              <th className="px-3 py-2 font-medium">Kind</th>
              <th className="px-3 py-2 text-right font-medium">Amount</th>
              <th className="px-3 py-2 text-right font-medium">NAV</th>
              <th className="px-3 py-2 text-right font-medium">Units</th>
              <th className="px-3 py-2 text-right font-medium">Units left</th>
              <th className="px-3 py-2 text-right font-medium">Cost left</th>
              <th className="px-3 py-2">
                <span className="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {holding.lots.map((lot) => (
              <Fragment key={lot.id}>
                <tr className={lot.skipped ? 'text-muted-foreground' : undefined}>
                  <td className="px-3 py-2 whitespace-nowrap">{formatDate(lot.buy_date)}</td>
                  <td className="px-3 py-2">
                    <span className="flex flex-wrap items-center gap-1">
                      {KIND_LABELS[lot.kind]}
                      {lot.skipped && <Badge variant="outline">Skipped</Badge>}
                      {lot.edited && !lot.skipped && <Badge variant="outline">Edited</Badge>}
                    </span>
                    {lot.note && <div className="text-muted-foreground text-xs">{lot.note}</div>}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">
                    {lot.skipped ? '—' : inr(lot.amount)}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">
                    {lot.skipped ? '—' : formatNav(lot.nav)}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">{formatUnits(lot.units)}</td>
                  <td className="px-3 py-2 text-right tabular-nums">
                    {formatUnits(lot.units_remaining)}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">{inr(lot.cost_remaining)}</td>
                  <td className="px-3 py-2">
                    <span className="flex justify-end gap-1">
                      <Button size="sm" variant="ghost" onClick={() => onEdit(lot)}>
                        {lot.skipped ? 'Unskip' : 'Edit'}
                      </Button>
                      {lot.kind === 'sip' && !lot.skipped && lot.sales.length === 0 && (
                        <Button
                          size="sm"
                          variant="ghost"
                          disabled={skip.isPending}
                          onClick={() =>
                            skip.mutate({
                              id: lot.id,
                              body: {
                                buy_date: lot.buy_date,
                                amount: lot.amount,
                                note: lot.note,
                                skipped: true,
                              },
                            })
                          }
                        >
                          Skip
                        </Button>
                      )}
                      {lot.kind === 'lump_sum' && lot.sales.length === 0 && (
                        <Button
                          size="sm"
                          variant="ghost"
                          disabled={remove.isPending}
                          onClick={() => {
                            if (confirm(`Delete the ${formatDate(lot.buy_date)} lump sum?`)) {
                              remove.mutate(lot.id)
                            }
                          }}
                        >
                          Delete
                        </Button>
                      )}
                    </span>
                  </td>
                </tr>
                {lot.sales.map((sale) => (
                  <tr key={`sale-${sale.id}`} className="bg-muted/30 text-muted-foreground text-xs">
                    <td className="px-3 py-1.5 pl-6 whitespace-nowrap">
                      {formatDate(sale.sale_date)}
                    </td>
                    <td className="px-3 py-1.5" colSpan={2}>
                      Sold {formatUnits(sale.units)} units for {inr(sale.amount)}
                    </td>
                    <td className="px-3 py-1.5 text-right tabular-nums">{formatNav(sale.nav)}</td>
                    <td className="px-3 py-1.5" colSpan={3} />
                    <td className="px-3 py-1.5">
                      <span className="flex justify-end">
                        <Button
                          size="sm"
                          variant="ghost"
                          disabled={undo.isPending}
                          aria-label={`Undo the ${formatDate(sale.sale_date)} sale of ${formatUnits(sale.units)} units`}
                          onClick={() => undo.mutate(sale.id)}
                        >
                          <Undo2 /> Undo
                        </Button>
                      </span>
                    </td>
                  </tr>
                ))}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
