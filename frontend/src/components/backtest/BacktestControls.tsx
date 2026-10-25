import { Loader2, Plus, X } from 'lucide-react'
import { cloneElement, isValidElement, type ReactElement, type ReactNode } from 'react'

import type { Schemas } from '@/api/client'
import { Field as BaseField } from '@/components/Field'
import { InfoTip } from '@/components/InfoTip'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { NativeSelect } from '@/components/ui/native-select'
import {
  FREQUENCY_LABELS,
  STRATEGY_LABELS,
  blankPosition,
  blankTrade,
  type BacktestForm,
  type Frequency,
  type PositionRow,
  type Strategy,
  type TradeRow,
} from '@/lib/backtest'
import { REBALANCE_LABELS } from '@/lib/buckets'
import { cn } from '@/lib/utils'

type Bucket = Schemas['BucketOut']

type Props = {
  buckets: Bucket[]
  bucket: Bucket | null
  onBucket: (id: number | null) => void
  form: BacktestForm
  onForm: (form: BacktestForm) => void
  onRun: () => void
  running: boolean
}

/** A compact label above one form control; the control gets the label's id. */
function Field({
  label,
  children,
  info,
}: {
  label: string
  children: ReactElement<{ id?: string }>
  info?: ReactNode
}) {
  return (
    <BaseField label={label} info={info} size="sm">
      {(id) => (isValidElement(children) ? cloneElement(children, { id }) : children)}
    </BaseField>
  )
}

function Money({
  label,
  value,
  onChange,
}: {
  label: string
  value: string
  onChange: (value: string) => void
}) {
  return (
    <Field label={label}>
      <Input inputMode="decimal" value={value} onChange={(event) => onChange(event.target.value)} />
    </Field>
  )
}

function Segmented<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: T
  options: Record<T, string>
  onChange: (value: T) => void
}) {
  return (
    <div role="radiogroup" aria-label={label} className="bg-muted flex rounded-md p-0.5">
      {(Object.keys(options) as T[]).map((key) => (
        <button
          key={key}
          type="button"
          role="radio"
          aria-checked={value === key}
          onClick={() => onChange(key)}
          className={cn(
            'flex-1 rounded px-1.5 py-1 text-sm whitespace-nowrap',
            value === key ? 'bg-background font-medium shadow-sm' : 'text-muted-foreground',
          )}
        >
          {options[key]}
        </button>
      ))}
    </div>
  )
}

/** The left column: which bucket, which strategy, its inputs, and Run (Friday's layout). */
export function BacktestControls({
  buckets,
  bucket,
  onBucket,
  form,
  onForm,
  onRun,
  running,
}: Props) {
  const set = (patch: Partial<BacktestForm>) => onForm({ ...form, ...patch })
  const funds = bucket?.funds.map((member) => member.fund) ?? []

  return (
    <form
      aria-label="Backtest settings"
      className="flex flex-col gap-4"
      onSubmit={(event) => {
        event.preventDefault()
        onRun()
      }}
    >
      <Field label="Model">
        <NativeSelect
          value={bucket?.id ?? ''}
          onChange={(event) => onBucket(event.target.value ? Number(event.target.value) : null)}
        >
          <option value="">Choose a model…</option>
          {buckets.map((b) => (
            <option key={b.id} value={b.id}>
              {b.name}
            </option>
          ))}
        </NativeSelect>
      </Field>

      <Segmented<Strategy>
        label="Strategy"
        value={form.strategy}
        options={STRATEGY_LABELS}
        onChange={(strategy) => set({ strategy })}
      />

      {form.strategy === 'regular' && (
        <>
          <Money
            label="Lump sum (₹)"
            value={form.capital}
            onChange={(capital) => set({ capital })}
          />
          <Field label="Rebalance">
            <NativeSelect
              value={form.rebalance}
              onChange={(event) =>
                set({ rebalance: event.target.value as BacktestForm['rebalance'] })
              }
            >
              <option value="">
                Model’s own ({bucket ? REBALANCE_LABELS[bucket.rebalance].toLowerCase() : '—'})
              </option>
              {(Object.keys(REBALANCE_LABELS) as (keyof typeof REBALANCE_LABELS)[]).map((key) => (
                <option key={key} value={key}>
                  {REBALANCE_LABELS[key]}
                </option>
              ))}
            </NativeSelect>
          </Field>
        </>
      )}
      {form.strategy === 'sip' && (
        <>
          <Money
            label="SIP amount (₹)"
            value={form.amount}
            onChange={(amount) => set({ amount })}
          />
          <FrequencyField value={form.frequency} onChange={(frequency) => set({ frequency })} />
        </>
      )}
      {form.strategy === 'swp' && (
        <>
          <Money
            label="Starting corpus (₹)"
            value={form.corpus}
            onChange={(corpus) => set({ corpus })}
          />
          <Money
            label="Withdraw each time (₹)"
            value={form.withdrawal}
            onChange={(withdrawal) => set({ withdrawal })}
          />
          <FrequencyField value={form.frequency} onChange={(frequency) => set({ frequency })} />
        </>
      )}
      {form.strategy === 'custom' && <CustomBuilder form={form} set={set} funds={funds} />}

      <div className="grid gap-2">
        {form.strategy !== 'custom' && (
          <Field label="From" info="Blank: from the first date every fund has a NAV.">
            <Input
              type="date"
              value={form.start}
              onChange={(event) => set({ start: event.target.value })}
            />
          </Field>
        )}
        <Field label="To" info="Blank: to the latest NAV.">
          <Input
            type="date"
            value={form.end}
            onChange={(event) => set({ end: event.target.value })}
          />
        </Field>
      </div>
      <Field label="Risk-free rate (% a year)" info="Used for Sharpe and Sortino.">
        <Input
          inputMode="decimal"
          value={form.riskFree}
          onChange={(event) => set({ riskFree: event.target.value })}
        />
      </Field>

      <Button type="submit" disabled={!bucket || running}>
        {running && <Loader2 className="animate-spin" />}
        Run backtest
      </Button>
    </form>
  )
}

function FrequencyField({
  value,
  onChange,
}: {
  value: Frequency
  onChange: (f: Frequency) => void
}) {
  return (
    <Field label="Every">
      <NativeSelect value={value} onChange={(event) => onChange(event.target.value as Frequency)}>
        {(Object.keys(FREQUENCY_LABELS) as Frequency[]).map((key) => (
          <option key={key} value={key}>
            {FREQUENCY_LABELS[key]}
          </option>
        ))}
      </NativeSelect>
    </Field>
  )
}

type FundRef = Schemas['FundRef']

function FundSelect({
  funds,
  value,
  onChange,
  label,
}: {
  funds: FundRef[]
  value: number | null
  onChange: (id: number | null) => void
  label: string
}) {
  return (
    <NativeSelect
      aria-label={label}
      value={value ?? ''}
      onChange={(event) => onChange(event.target.value ? Number(event.target.value) : null)}
    >
      <option value="">Fund…</option>
      {funds.map((fund) => (
        <option key={fund.id} value={fund.id}>
          {fund.name}
        </option>
      ))}
    </NativeSelect>
  )
}

function CustomBuilder({
  form,
  set,
  funds,
}: {
  form: BacktestForm
  set: (patch: Partial<BacktestForm>) => void
  funds: FundRef[]
}) {
  const setPosition = (i: number, patch: Partial<PositionRow>) =>
    set({ positions: form.positions.map((row, j) => (j === i ? { ...row, ...patch } : row)) })
  const setTrade = (i: number, patch: Partial<TradeRow>) =>
    set({ trades: form.trades.map((row, j) => (j === i ? { ...row, ...patch } : row)) })

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-1.5">
        <div className="flex-1">
          <Segmented
            label="Custom timeline as"
            value={form.customMode}
            options={{ positions: 'Positions', trades: 'Trades' }}
            onChange={(customMode) => set({ customMode })}
          />
        </div>
        <InfoTip label="Custom timeline">
          {form.customMode === 'positions'
            ? 'Hold a fund between two dates; leave the exit empty to hold to the end. Several positions model switches.'
            : 'Buys and sells at that day’s NAV, or the next NAV date on holidays.'}
        </InfoTip>
      </div>
      {form.customMode === 'positions' ? (
        <>
          {form.positions.map((row, i) => (
            <fieldset key={i} className="bg-muted/40 flex flex-col gap-2 rounded-md border p-2">
              <legend className="sr-only">Position {i + 1}</legend>
              <div className="flex gap-1">
                <FundSelect
                  label={`Position ${i + 1} fund`}
                  funds={funds}
                  value={row.fundId}
                  onChange={(fundId) => setPosition(i, { fundId })}
                />
                <Button
                  type="button"
                  size="icon"
                  variant="ghost"
                  aria-label={`Remove position ${i + 1}`}
                  disabled={form.positions.length === 1}
                  onClick={() => set({ positions: form.positions.filter((_, j) => j !== i) })}
                >
                  <X />
                </Button>
              </div>
              <div className="grid gap-2">
                <Field label="Entry">
                  <Input
                    type="date"
                    value={row.entry}
                    onChange={(e) => setPosition(i, { entry: e.target.value })}
                  />
                </Field>
                <Field label="Exit">
                  <Input
                    type="date"
                    value={row.exit}
                    onChange={(e) => setPosition(i, { exit: e.target.value })}
                  />
                </Field>
              </div>
              <Money
                label="Amount (₹)"
                value={row.amount}
                onChange={(amount) => setPosition(i, { amount })}
              />
            </fieldset>
          ))}
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => set({ positions: [...form.positions, blankPosition()] })}
          >
            <Plus /> Add position
          </Button>
        </>
      ) : (
        <>
          {form.trades.map((row, i) => (
            <fieldset key={i} className="bg-muted/40 flex flex-col gap-2 rounded-md border p-2">
              <legend className="sr-only">Trade {i + 1}</legend>
              <div className="flex gap-1">
                <FundSelect
                  label={`Trade ${i + 1} fund`}
                  funds={funds}
                  value={row.fundId}
                  onChange={(fundId) => setTrade(i, { fundId })}
                />
                <Button
                  type="button"
                  size="icon"
                  variant="ghost"
                  aria-label={`Remove trade ${i + 1}`}
                  disabled={form.trades.length === 1}
                  onClick={() => set({ trades: form.trades.filter((_, j) => j !== i) })}
                >
                  <X />
                </Button>
              </div>
              <div className="grid gap-2">
                <Field label="Date">
                  <Input
                    type="date"
                    value={row.date}
                    onChange={(e) => setTrade(i, { date: e.target.value })}
                  />
                </Field>
                <Field label="Side">
                  <NativeSelect
                    value={row.side}
                    onChange={(e) => {
                      const side = e.target.value as TradeRow['side']
                      setTrade(i, {
                        side,
                        by: side === 'buy' && row.by === 'all' ? 'amount' : row.by,
                      })
                    }}
                  >
                    <option value="buy">Buy</option>
                    <option value="sell">Sell</option>
                  </NativeSelect>
                </Field>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <Field label="By">
                  <NativeSelect
                    value={row.by}
                    onChange={(e) => setTrade(i, { by: e.target.value as TradeRow['by'] })}
                  >
                    <option value="amount">₹ amount</option>
                    <option value="units">Units</option>
                    {row.side === 'sell' && <option value="all">Everything</option>}
                  </NativeSelect>
                </Field>
                {row.by !== 'all' && (
                  <Field label={row.by === 'units' ? 'Units' : 'Amount (₹)'}>
                    <Input
                      inputMode="decimal"
                      value={row.quantity}
                      onChange={(e) => setTrade(i, { quantity: e.target.value })}
                    />
                  </Field>
                )}
              </div>
            </fieldset>
          ))}
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => set({ trades: [...form.trades, blankTrade()] })}
          >
            <Plus /> Add trade
          </Button>
        </>
      )}
    </div>
  )
}
