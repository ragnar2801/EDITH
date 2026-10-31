import { RotateCcw, X } from 'lucide-react'
import { toast } from 'sonner'

import { useSaveModel, useTrackAnyFund } from '@/api/queries'
import { ErrorText } from '@/components/Field'
import { InfoTip } from '@/components/InfoTip'
import { InstrumentSearch } from '@/components/InstrumentSearch'
import { FundName } from '@/components/models/FundName'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useConfirm } from '@/hooks/use-confirm'
import { modelSplit, splitModified, type SplitRow } from '@/lib/backtest'
import type { Model } from '@/lib/models'
import { cn } from '@/lib/utils'
import { fromBasisPoints, totalBasisPoints } from '@/lib/weights'

/** The funds and weights a backtest runs; changing them leaves the model alone. */
export function SplitEditor({
  model,
  split,
  onChange,
}: {
  model: Model
  split: SplitRow[]
  onChange: (split: SplitRow[]) => void
}) {
  const modified = splitModified(split, model)
  const total = totalBasisPoints(split.map((row) => row.weight))
  const track = useTrackAnyFund()
  const save = useSaveModel()
  const confirm = useConfirm()

  async function saveToModel() {
    const yes = await confirm({
      title: `Save this split to ${model.name}?`,
      description: 'Invest and drift use the new weights.',
      action: 'Save to model',
    })
    if (!yes) return
    save.mutate(
      {
        id: model.id,
        body: {
          name: model.name,
          description: model.description,
          rebalance: model.rebalance,
          benchmark_id: model.benchmark?.fund.id ?? null,
          funds: split.map((row) => ({ instrument_id: row.fund.id, weight: row.weight.trim() })),
        },
      },
      { onSuccess: () => toast.success(`${model.name} saved`) },
    )
  }

  return (
    <fieldset className="flex min-w-0 flex-col gap-2">
      <legend className="mb-1 flex w-full items-center gap-1.5 text-xs font-medium">
        <span className="text-muted-foreground">Split</span>
        <InfoTip label="Split">Try other weights or funds; the model stays as it is.</InfoTip>
        {modified && <Badge variant="secondary">Modified</Badge>}
        <Badge
          variant="outline"
          className={cn('ml-auto', total === 10_000 ? 'text-positive' : 'text-destructive')}
        >
          {total === null ? '?' : fromBasisPoints(total)}%
        </Badge>
      </legend>
      <ul className="flex flex-col divide-y rounded-md border">
        {split.map((row, index) => (
          <li key={row.fund.id} className="flex items-center gap-2 px-2 py-1.5 text-sm">
            <FundName fund={row.fund} />
            <span className="ml-auto flex shrink-0 items-center gap-0.5">
              <Input
                aria-label={`Weight of ${row.fund.name}`}
                className="h-8 w-16 text-right"
                inputMode="decimal"
                value={row.weight}
                onChange={(event) =>
                  onChange(
                    split.map((r, i) => (i === index ? { ...r, weight: event.target.value } : r)),
                  )
                }
              />
              <Button
                type="button"
                size="icon"
                variant="ghost"
                className="size-7"
                aria-label={`Remove ${row.fund.name}`}
                onClick={() => onChange(split.filter((_, i) => i !== index))}
              >
                <X />
              </Button>
            </span>
          </li>
        ))}
      </ul>
      <InstrumentSearch
        kind="mutual_fund"
        label="Add a fund to the split"
        placeholder="Add a fund"
        onSelect={(fund) => {
          if (split.some((row) => row.fund.id === fund.id)) return
          onChange([...split, { fund, weight: '' }])
          if (!model.funds.some((member) => member.fund.id === fund.id)) {
            track.mutate(fund.id, {
              onError: (error) => toast.error(`${fund.name}: ${error.message}`),
            })
          }
        }}
      />
      {modified && (
        <div className="flex gap-2">
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={() => onChange(modelSplit(model))}
          >
            <RotateCcw />
            Reset
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="ml-auto"
            disabled={total !== 10_000 || save.isPending}
            onClick={saveToModel}
          >
            Save to model
          </Button>
        </div>
      )}
      <ErrorText error={save.error} />
    </fieldset>
  )
}
