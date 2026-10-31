import { ChevronDown, ChevronRight, X } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { toast } from 'sonner'

import { useSaveBucket } from '@/api/queries'
import { ErrorText, Field } from '@/components/Field'
import { InfoTip } from '@/components/InfoTip'
import { InstrumentSearch } from '@/components/InstrumentSearch'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { NativeSelect } from '@/components/ui/native-select'
import { REBALANCE_LABELS, type Bucket, type Rebalance } from '@/lib/buckets'
import type { ModelDraft } from '@/lib/models'
import { cn } from '@/lib/utils'
import { equalWeights, fromBasisPoints, totalBasisPoints } from '@/lib/weights'

import { FundName } from './FundName'

const BENCHMARK_INFO = 'Backtests compare the model with the same money in this fund.'
const REBALANCE_INFO = 'How often a backtest resets the funds to their target weights.'

/** A model: name, funds with weights adding up to exactly 100, rebalance, benchmark. */
export function ModelEditor({
  initial,
  onSaved,
  onCancel,
}: {
  initial: ModelDraft
  onSaved: (bucket: Bucket) => void
  onCancel: () => void
}) {
  const [draft, setDraft] = useState(initial)
  const [more, setMore] = useState(initial.description !== '')
  const save = useSaveBucket()
  const total = totalBasisPoints(draft.funds.map((member) => member.weight))

  function update(patch: Partial<ModelDraft>) {
    setDraft((current) => ({ ...current, ...patch }))
  }

  function setWeight(index: number, weight: string) {
    update({
      funds: draft.funds.map((member, i) => (i === index ? { ...member, weight } : member)),
    })
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    save.mutate(
      {
        id: draft.id,
        body: {
          name: draft.name,
          description: draft.description || null,
          rebalance: draft.rebalance,
          benchmark_id: draft.benchmark?.id ?? null,
          funds: draft.funds.map((member) => ({
            instrument_id: member.fund.id,
            weight: member.weight.trim(),
          })),
        },
      },
      {
        onSuccess: (saved) => {
          toast.success(`${saved.name} saved`)
          onSaved(saved)
        },
      },
    )
  }

  return (
    <form aria-label="Model" className="flex flex-col gap-6" onSubmit={submit}>
      <div className="grid gap-4 sm:grid-cols-[2fr_1fr]">
        <Field label="Name">
          {(id) => (
            <Input
              id={id}
              value={draft.name}
              placeholder="Core 40/25/20/15"
              onChange={(event) => update({ name: event.target.value })}
              required
              maxLength={120}
            />
          )}
        </Field>
        <Field label="Rebalance" info={REBALANCE_INFO}>
          {(id) => (
            <NativeSelect
              id={id}
              value={draft.rebalance}
              onChange={(event) => update({ rebalance: event.target.value as Rebalance })}
            >
              {(Object.keys(REBALANCE_LABELS) as Rebalance[]).map((key) => (
                <option key={key} value={key}>
                  {REBALANCE_LABELS[key]}
                </option>
              ))}
            </NativeSelect>
          )}
        </Field>
      </div>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1 flex w-full items-center justify-between gap-2 text-sm font-medium">
          <span className="flex items-center gap-1.5">
            Funds
            <InfoTip label="Funds">
              Weights in %, up to 2 decimals, adding up to exactly 100.
            </InfoTip>
          </span>
          <span className="flex items-center gap-2">
            <Badge
              variant="outline"
              className={cn(total === 10_000 ? 'text-positive' : 'text-destructive')}
            >
              Total {total === null ? '?' : fromBasisPoints(total)}%
            </Badge>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              disabled={draft.funds.length === 0}
              onClick={() => {
                const weights = equalWeights(draft.funds.length)
                update({
                  funds: draft.funds.map((member, i) => ({ ...member, weight: weights[i] })),
                })
              }}
            >
              Equal weights
            </Button>
          </span>
        </legend>
        {draft.funds.length > 0 && (
          <ul className="flex flex-col divide-y rounded-md border">
            {draft.funds.map((member, index) => (
              <li key={member.fund.id} className="flex items-center gap-3 px-3 py-2">
                <FundName fund={member.fund} />
                <span className="ml-auto flex shrink-0 items-center gap-1">
                  <Input
                    aria-label={`Weight of ${member.fund.name}`}
                    className="w-20 text-right"
                    inputMode="decimal"
                    value={member.weight}
                    onChange={(event) => setWeight(index, event.target.value)}
                  />
                  <span className="text-muted-foreground text-sm">%</span>
                  <Button
                    type="button"
                    size="icon"
                    variant="ghost"
                    aria-label={`Remove ${member.fund.name}`}
                    onClick={() => update({ funds: draft.funds.filter((_, i) => i !== index) })}
                  >
                    <X />
                  </Button>
                </span>
              </li>
            ))}
          </ul>
        )}
        <InstrumentSearch
          kind="mutual_fund"
          label="Add a fund"
          placeholder="Add a fund"
          onSelect={(fund) => {
            if (draft.funds.some((member) => member.fund.id === fund.id)) return
            update({ funds: [...draft.funds, { fund, weight: '' }] })
          }}
        />
      </fieldset>

      <div className="flex flex-col gap-1.5">
        <span className="flex items-center gap-1.5 text-sm font-medium">
          Benchmark
          <InfoTip label="Benchmark">{BENCHMARK_INFO}</InfoTip>
        </span>
        {draft.benchmark ? (
          <div className="flex items-center gap-3 rounded-md border px-3 py-2">
            <FundName fund={draft.benchmark} />
            <Button
              type="button"
              size="sm"
              variant="ghost"
              className="ml-auto"
              onClick={() => update({ benchmark: null })}
            >
              Remove
            </Button>
          </div>
        ) : (
          <InstrumentSearch
            kind="mutual_fund"
            label="Choose a benchmark"
            placeholder="Nifty 50 index fund"
            onSelect={(fund) => update({ benchmark: fund })}
          />
        )}
      </div>

      <div className="flex flex-col gap-4">
        <button
          type="button"
          aria-expanded={more}
          className="text-muted-foreground hover:text-foreground flex w-fit items-center gap-1 text-sm"
          onClick={() => setMore(!more)}
        >
          {more ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
          More options
        </button>
        {more && (
          <Field label="Description">
            {(id) => (
              <Input
                id={id}
                value={draft.description}
                maxLength={500}
                onChange={(event) => update({ description: event.target.value })}
              />
            )}
          </Field>
        )}
      </div>

      <ErrorText error={save.error} />
      <div className="flex flex-wrap justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={save.isPending}>
          {save.isPending ? 'Saving…' : 'Save model'}
        </Button>
      </div>
    </form>
  )
}
