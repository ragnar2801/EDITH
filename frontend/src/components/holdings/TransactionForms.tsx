import { ChevronDown, ChevronRight } from 'lucide-react'
import { useState, type FormEvent, type ReactNode } from 'react'
import { toast } from 'sonner'

import { useAddLumpSum, useSaveSip, useSell, useUpdateLot, type Holding } from '@/api/queries'
import { ErrorText, Field } from '@/components/Field'
import { Button } from '@/components/ui/button'
import { DialogFooter } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { hasUnits, KIND_LABELS, type Lot, type Sip } from '@/lib/holdings'
import { formatUnits, inr } from '@/lib/money'
import { formatDate, todayIst } from '@/lib/time'

/** Optional fields, folded away until asked for. */
function MoreOptions({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="flex flex-col gap-4">
      <button
        type="button"
        aria-expanded={open}
        className="text-muted-foreground hover:text-foreground flex w-fit items-center gap-1 text-sm"
        onClick={() => setOpen(!open)}
      >
        {open ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
        More options
      </button>
      {open && children}
    </div>
  )
}

function FormShell({
  label,
  error,
  pending,
  submit,
  onSubmit,
  onCancel,
  children,
}: {
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
    <form aria-label={label} className="flex flex-col gap-4" onSubmit={handle}>
      {children}
      <ErrorText error={error} />
      <DialogFooter>
        <Button type="button" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={pending}>
          {submit}
        </Button>
      </DialogFooter>
    </form>
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
              placeholder="10,000"
              value={draft.amount}
              onChange={(event) => update({ amount: event.target.value })}
            />
          )}
        </Field>
      </div>
      <MoreOptions>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="NAV" info="Blank: the fund's NAV on that date.">
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
            label="Units"
            info="Blank: amount ÷ NAV, to 3 places. Type your statement's to override."
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
        <Field label="Note">
          {(id) => (
            <Input
              id={id}
              maxLength={200}
              value={draft.note}
              onChange={(event) => update({ note: event.target.value })}
            />
          )}
        </Field>
      </MoreOptions>
    </>
  )
}

/** The fund's latest NAV date, so a blank NAV can be looked up (today has none until the
 * evening, nor on weekends); today when no NAVs are downloaded yet. */
function defaultDate(holding: Holding): string {
  return holding.coverage.last ?? todayIst()
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

export function LumpSumForm({ holding, onDone }: { holding: Holding; onDone: () => void }) {
  const add = useAddLumpSum(holding)
  const [draft, setDraft] = useState<BuyDraft>({
    buy_date: defaultDate(holding),
    amount: '',
    nav: '',
    units: '',
    note: '',
  })
  return (
    <FormShell
      label="Lump sum"
      error={add.error}
      pending={add.isPending}
      submit="Save"
      onSubmit={() =>
        add.mutate(buyBody(draft), {
          onSuccess: () => {
            toast.success(`${inr(draft.amount.trim())} added to ${holding.fund.name}`)
            onDone()
          },
        })
      }
      onCancel={onDone}
    >
      <BuyFields draft={draft} update={(patch) => setDraft({ ...draft, ...patch })} />
    </FormShell>
  )
}

export function LotEditForm({
  holding,
  lot,
  onDone,
}: {
  holding: Holding
  lot: Lot
  onDone: () => void
}) {
  const save = useUpdateLot(holding.fund.id)
  const [draft, setDraft] = useState<BuyDraft>({
    buy_date: lot.buy_date,
    amount: lot.amount,
    nav: lot.skipped ? '' : lot.nav,
    units: lot.skipped ? '' : lot.units,
    note: lot.note ?? '',
  })
  return (
    <FormShell
      label="Purchase"
      error={save.error}
      pending={save.isPending}
      submit="Save"
      onSubmit={() =>
        save.mutate(
          { id: lot.id, body: { ...buyBody(draft), skipped: false } },
          {
            onSuccess: () => {
              toast.success('Purchase saved')
              onDone()
            },
          },
        )
      }
      onCancel={onDone}
    >
      <BuyFields draft={draft} update={(patch) => setDraft({ ...draft, ...patch })} />
    </FormShell>
  )
}

export function SipForm({
  holding,
  sip,
  onDone,
}: {
  holding: Holding
  sip?: Sip
  onDone: () => void
}) {
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
    <FormShell
      label="SIP"
      error={save.error}
      pending={save.isPending}
      submit={sip ? 'Save' : 'Start SIP'}
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
          {
            onSuccess: () => {
              toast.success(sip ? 'SIP saved' : `SIP started in ${holding.fund.name}`)
              onDone()
            },
          },
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
              placeholder="5,000"
              value={draft.amount}
              onChange={(event) => update({ amount: event.target.value })}
            />
          )}
        </Field>
        <Field
          label="SIP day"
          info="Day of the month, 1 to 28. Each instalment uses the first NAV on or after it."
        >
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
        <Field label="End date" info="Blank while the SIP is running.">
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
      <MoreOptions>
        <Field label="Note">
          {(id) => (
            <Input
              id={id}
              maxLength={200}
              value={draft.note}
              onChange={(event) => update({ note: event.target.value })}
            />
          )}
        </Field>
      </MoreOptions>
    </FormShell>
  )
}

export function SellForm({ holding, onDone }: { holding: Holding; onDone: () => void }) {
  const sell = useSell(holding.fund.id)
  const lots = holding.lots.filter(hasUnits)
  const [saleDate, setSaleDate] = useState(defaultDate(holding))
  const [nav, setNav] = useState('')
  const [units, setUnits] = useState<Record<number, string>>({})
  const picked = lots.filter((lot) => (units[lot.id] ?? '').trim())
  return (
    <FormShell
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
          {
            onSuccess: () => {
              toast.success(`Sold from ${holding.fund.name}`)
              onDone()
            },
          },
        )
      }
      onCancel={onDone}
    >
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
      {lots.length === 0 ? (
        <p className="text-muted-foreground text-sm">No units to sell.</p>
      ) : (
        <fieldset className="flex flex-col gap-1.5">
          <legend className="mb-1.5 text-sm font-medium">Units from each purchase</legend>
          <ul className="flex flex-col divide-y rounded-md border text-sm">
            {lots.map((lot) => (
              <li key={lot.id} className="flex flex-wrap items-center gap-3 px-3 py-2">
                <span className="min-w-0">
                  <span className="font-medium">{formatDate(lot.buy_date)}</span>{' '}
                  <span className="text-muted-foreground">
                    · {KIND_LABELS[lot.kind]} · {formatUnits(lot.units_remaining)} left
                  </span>
                </span>
                <span className="ml-auto flex items-center gap-1">
                  <Input
                    aria-label={`Units to sell from the ${formatDate(lot.buy_date)} purchase`}
                    className="w-28 text-right"
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
        </fieldset>
      )}
      <MoreOptions>
        <Field label="NAV" info="Blank: the fund's NAV on the sale date.">
          {(id) => (
            <Input
              id={id}
              inputMode="decimal"
              value={nav}
              onChange={(event) => setNav(event.target.value)}
            />
          )}
        </Field>
      </MoreOptions>
    </FormShell>
  )
}
