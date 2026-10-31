import { Download, GitCompareArrows, X } from 'lucide-react'
import { useState } from 'react'
import { useLocation, useSearchParams } from 'react-router'
import { toast } from 'sonner'

import { useBuckets, useCompare, useModels, useTrackAnyFund } from '@/api/queries'
import { ComparisonView } from '@/components/compare/ComparisonView'
import { Swatch } from '@/components/compare/Swatch'
import { EmptyState } from '@/components/EmptyState'
import { ErrorText } from '@/components/Field'
import { InstrumentSearch } from '@/components/InstrumentSearch'
import { Loading } from '@/components/Loading'
import { PageHeader } from '@/components/PageHeader'
import { RouteTabs } from '@/components/RouteTabs'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { NativeSelect } from '@/components/ui/native-select'
import { bucketLabel } from '@/lib/buckets'
import {
  COMPARE_PATHS,
  ROLLING_YEARS,
  named,
  seriesColor,
  type CompareKind,
  type Comparison,
} from '@/lib/compare'
import { formatDate } from '@/lib/time'

type Rolling = (typeof ROLLING_YEARS)[number]

const TABS: Record<CompareKind, string> = { funds: 'Funds', buckets: 'Buckets', models: 'Models' }
const NOUN: Record<CompareKind, string> = { funds: 'fund', buckets: 'bucket', models: 'model' }

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

function kindOf(pathname: string): CompareKind {
  const found = (Object.keys(COMPARE_PATHS) as CompareKind[]).find(
    (kind) => COMPARE_PATHS[kind] === pathname,
  )
  return found ?? 'funds'
}

/** Funds, buckets or models side by side: the picks, the benchmark and the dates all live
 * in the URL. */
export function ComparePage() {
  const { pathname } = useLocation()
  const kind = kindOf(pathname)
  const [params, setParams] = useSearchParams()
  const ids = readIds(params.get('ids'))
  const start = params.get('start') ?? undefined
  const benchmark = Number(params.get('benchmark')) || undefined
  const chosen = (ROLLING_YEARS as readonly number[]).includes(Number(params.get('rolling')))
    ? (Number(params.get('rolling')) as Rolling)
    : undefined
  // Unless one is chosen, rolling periods are 3 years, or 1 when the dates are shorter.
  const [windowYears, setWindowYears] = useState<number>()
  const rolling = chosen ?? (windowYears !== undefined && windowYears < 3 ? 1 : 3)
  const [choosingBenchmark, setChoosingBenchmark] = useState(false)
  const comparison = useCompare(kind, { ids, benchmark, start, rollingYears: rolling })
  const data = comparison.data && named(kind, comparison.data)
  const years = data?.window ? Number(data.window.years) : undefined
  if (years !== windowYears) setWindowYears(years)

  function update(changes: Record<string, string | null>) {
    const next = new URLSearchParams(params)
    for (const [key, value] of Object.entries(changes)) {
      if (value === null) next.delete(key)
      else next.set(key, value)
    }
    setParams(next, { replace: true })
  }

  const setIds = (next: number[]) => update({ ids: next.length ? next.join(',') : null })
  const add = (id: number) => {
    if (!ids.includes(id)) setIds([...ids, id])
  }

  const body = (
    <>
      <div className="flex max-w-xl flex-col gap-3">
        <Picker kind={kind} picked={ids} onAdd={add} />
      </div>
      {ids.length === 0 ? (
        <EmptyState icon={GitCompareArrows} title={`Add ${kind} to compare them`} />
      ) : (
        <>
          <Picks
            kind={kind}
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
              <ComparisonView
                kind={kind}
                comparison={data}
                rolling={rolling}
                onRolling={(years) => update({ rolling: String(years) })}
              />
            )
          )}
        </>
      )}
    </>
  )

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Compare"
        meta={data?.window && <WindowMeta comparison={data} />}
        actions={
          ids.length > 0 && (
            <Button variant="outline" onClick={() => setChoosingBenchmark(true)}>
              {data?.benchmark ? `vs ${data.benchmark.name}` : 'Choose benchmark'}
            </Button>
          )
        }
      />
      <RouteTabs
        label="Compare"
        tabs={(Object.keys(TABS) as CompareKind[]).map((tab) => ({
          path: COMPARE_PATHS[tab],
          label: TABS[tab],
          content: <div className="flex flex-col gap-6">{body}</div>,
        }))}
      />
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

/** A fund search, or a list of the buckets or models not picked yet. */
function Picker({
  kind,
  picked,
  onAdd,
}: {
  kind: CompareKind
  picked: number[]
  onAdd: (id: number) => void
}) {
  const buckets = useBuckets()
  const models = useModels()
  if (kind === 'funds') {
    return (
      <InstrumentSearch
        kind="mutual_fund"
        label="Add a fund"
        placeholder="Add a fund"
        onSelect={(fund) => onAdd(fund.id)}
      />
    )
  }
  const options =
    kind === 'buckets'
      ? (buckets.data ?? []).map((bucket) => ({ id: bucket.id, name: bucketLabel(bucket) }))
      : (models.data ?? []).map((model) => ({ id: model.id, name: model.name }))
  const left = options.filter((option) => !picked.includes(option.id))
  return (
    <NativeSelect
      aria-label={`Add a ${NOUN[kind]}`}
      value=""
      disabled={left.length === 0}
      onChange={(event) => event.target.value && onAdd(Number(event.target.value))}
    >
      <option value="">Add a {NOUN[kind]}</option>
      {left.map((option) => (
        <option key={option.id} value={option.id}>
          {option.name}
        </option>
      ))}
    </NativeSelect>
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

/** The picks as chips in their chart colours, with a way to get NAVs for new funds. */
function Picks({
  kind,
  ids,
  comparison,
  onRemove,
}: {
  kind: CompareKind
  ids: number[]
  comparison: Comparison | undefined
  onRemove: (id: number) => void
}) {
  const track = useTrackAnyFund()
  const byId = new Map(comparison?.items.map((item) => [item.id, item]))

  return (
    <ul aria-label={`${TABS[kind]} compared`} className="flex flex-wrap gap-2">
      {ids.map((id, index) => {
        const item = byId.get(id)
        const missing = kind === 'funds' && item && item.data.first === null
        return (
          <li
            key={id}
            className="bg-card flex max-w-full items-center gap-2 rounded-md border py-1 pr-1 pl-2.5 text-sm"
          >
            <Swatch color={seriesColor(index)} />
            <span className="flex min-w-0 flex-col">
              <span className="truncate font-medium">{item?.name ?? '…'}</span>
              {item?.detail && (
                <span className="text-muted-foreground truncate text-xs">{item.detail}</span>
              )}
            </span>
            {missing && (
              <Button
                size="sm"
                variant="outline"
                disabled={track.isPending}
                onClick={() =>
                  track.mutate(id, {
                    onSuccess: () => toast.success(`NAVs downloaded for ${item.name}`),
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
              aria-label={`Remove ${item?.name ?? NOUN[kind]}`}
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

/** Which pick sets the start, and a way to start earlier without it (or include it again). */
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
  const names = new Map(comparison.items.map((item) => [item.id, item.name]))
  const leftOut = comparison.items.filter((item) => item.data.first !== null && !item.data.window)
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
      {leftOut.length > 0 && <span>Left out: {leftOut.map((item) => item.name).join(', ')}</span>}
      {hasStart && (
        <Button size="sm" variant="ghost" onClick={() => onStart(null)}>
          Include every one
        </Button>
      )}
    </div>
  )
}
