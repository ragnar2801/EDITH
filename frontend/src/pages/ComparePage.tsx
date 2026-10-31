import { Download, GitCompareArrows, X } from 'lucide-react'
import { useState } from 'react'
import { useSearchParams } from 'react-router'
import { toast } from 'sonner'

import { useCompareFunds, useTrackAnyFund } from '@/api/queries'
import { FundComparison } from '@/components/compare/FundComparison'
import { Swatch } from '@/components/compare/Swatch'
import { EmptyState } from '@/components/EmptyState'
import { ErrorText } from '@/components/Field'
import { InstrumentSearch } from '@/components/InstrumentSearch'
import { Loading } from '@/components/Loading'
import { PageHeader } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { ROLLING_YEARS, seriesColor, type Comparison } from '@/lib/compare'
import { planLabel } from '@/lib/instruments'
import { formatDate } from '@/lib/time'

type Rolling = (typeof ROLLING_YEARS)[number]

function readIds(value: string | null): number[] {
  return [
    ...new Set(
      (value ?? '')
        .split(',')
        .map(Number)
        .filter((id) => Number.isInteger(id) && id > 0),
    ),
  ]
}

/** Funds side by side: the picks, the benchmark and the dates all live in the URL. */
export function ComparePage() {
  const [params, setParams] = useSearchParams()
  const ids = readIds(params.get('ids'))
  const start = params.get('start') ?? undefined
  const benchmark = Number(params.get('benchmark')) || undefined
  const rolling = (ROLLING_YEARS as readonly number[]).includes(Number(params.get('rolling')))
    ? (Number(params.get('rolling')) as Rolling)
    : 3
  const [choosingBenchmark, setChoosingBenchmark] = useState(false)
  const comparison = useCompareFunds({ ids, benchmark, start, rollingYears: rolling })

  function update(changes: Record<string, string | null>) {
    const next = new URLSearchParams(params)
    for (const [key, value] of Object.entries(changes)) {
      if (value === null) next.delete(key)
      else next.set(key, value)
    }
    setParams(next, { replace: true })
  }

  const setIds = (next: number[]) => update({ ids: next.length ? next.join(',') : null })
  const data = comparison.data

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Compare"
        meta={data?.window && <WindowMeta comparison={data} />}
        actions={
          ids.length > 0 && (
            <Button variant="outline" onClick={() => setChoosingBenchmark(true)}>
              {data?.benchmark ? `vs ${data.benchmark.fund.name}` : 'Choose benchmark'}
            </Button>
          )
        }
      />
      <div className="flex max-w-xl flex-col gap-3">
        <InstrumentSearch
          kind="mutual_fund"
          label="Add a fund"
          placeholder="Add a fund"
          onSelect={(fund) => {
            if (!ids.includes(fund.id)) setIds([...ids, fund.id])
          }}
        />
      </div>
      {ids.length === 0 ? (
        <EmptyState icon={GitCompareArrows} title="Add funds to compare them" />
      ) : (
        <>
          <Picks
            ids={ids}
            comparison={data}
            onRemove={(id) => setIds(ids.filter((other) => other !== id))}
          />
          <WindowControl
            comparison={data}
            hasStart={Boolean(start)}
            onStart={(date) => update({ start: date })}
          />
          <ErrorText error={comparison.error} />
          {comparison.isPending ? (
            <Loading />
          ) : (
            data && (
              <FundComparison
                comparison={data}
                rolling={rolling}
                onRolling={(years) => update({ rolling: years === 3 ? null : String(years) })}
              />
            )
          )}
        </>
      )}
      <Dialog open={choosingBenchmark} onOpenChange={setChoosingBenchmark}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Benchmark</DialogTitle>
            <DialogDescription className="sr-only">
              Pick the fund to compare against
            </DialogDescription>
          </DialogHeader>
          <InstrumentSearch
            autoFocus
            kind="mutual_fund"
            label="Choose a benchmark"
            placeholder="Nifty 50 index fund"
            onSelect={(fund) => {
              update({ benchmark: String(fund.id) })
              setChoosingBenchmark(false)
            }}
          />
        </DialogContent>
      </Dialog>
    </div>
  )
}

function WindowMeta({ comparison }: { comparison: Comparison }) {
  const window = comparison.window!
  return (
    <span>
      {formatDate(window.start)} – {formatDate(window.end)} · {window.years} years
    </span>
  )
}

/** The picked funds as chips in their chart colours, with a way to get NAVs for new ones. */
function Picks({
  ids,
  comparison,
  onRemove,
}: {
  ids: number[]
  comparison: Comparison | undefined
  onRemove: (id: number) => void
}) {
  const track = useTrackAnyFund()
  const byId = new Map(comparison?.funds.map((row) => [row.fund.id, row]))

  return (
    <ul aria-label="Funds compared" className="flex flex-wrap gap-2">
      {ids.map((id, index) => {
        const row = byId.get(id)
        const missing = row && row.first_nav === null
        return (
          <li
            key={id}
            className="bg-card flex max-w-full items-center gap-2 rounded-md border py-1 pr-1 pl-2.5 text-sm"
          >
            <Swatch color={seriesColor(index)} />
            <span className="flex min-w-0 flex-col">
              <span className="truncate font-medium">{row?.fund.name ?? '…'}</span>
              {row && planLabel(row.fund) && (
                <span className="text-muted-foreground truncate text-xs">
                  {planLabel(row.fund)}
                </span>
              )}
            </span>
            {missing && (
              <Button
                size="sm"
                variant="outline"
                disabled={track.isPending}
                onClick={() =>
                  track.mutate(id, {
                    onSuccess: () => toast.success(`NAVs downloaded for ${row.fund.name}`),
                    onError: (error) => toast.error(error.message),
                  })
                }
              >
                <Download /> Get NAVs
              </Button>
            )}
            <Button
              size="icon"
              variant="ghost"
              className="size-7"
              aria-label={`Remove ${row?.fund.name ?? 'fund'}`}
              onClick={() => onRemove(id)}
            >
              <X />
            </Button>
          </li>
        )
      })}
    </ul>
  )
}

/** Which fund sets the start, and a way to start earlier without it (or include it again). */
function WindowControl({
  comparison,
  hasStart,
  onStart,
}: {
  comparison: Comparison | undefined
  hasStart: boolean
  onStart: (date: string | null) => void
}) {
  if (!comparison) return null
  const window = comparison.window
  const names = new Map(comparison.funds.map((row) => [row.fund.id, row.fund.name]))
  const leftOut = comparison.funds.filter((row) => row.first_nav !== null && row.window === null)
  const limiter = window?.limited_by ? names.get(window.limited_by) : undefined
  if (!limiter && leftOut.length === 0) return null

  return (
    <div className="text-muted-foreground flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
      {limiter && window?.earliest_start && (
        <>
          <span>Starts when {limiter} does</span>
          <Button size="sm" variant="outline" onClick={() => onStart(window.earliest_start)}>
            Start {formatDate(window.earliest_start)} without it
          </Button>
        </>
      )}
      {leftOut.length > 0 && (
        <span>Left out: {leftOut.map((row) => row.fund.name).join(', ')}</span>
      )}
      {hasStart && (
        <Button size="sm" variant="ghost" onClick={() => onStart(null)}>
          Include every fund
        </Button>
      )}
    </div>
  )
}
