import { useMemo, useState, type ReactNode } from 'react'

import { usePortfolioHistory, type Portfolio } from '@/api/queries'
import { LineChart, type ChartSeries } from '@/components/charts/LineChart'
import { ErrorText } from '@/components/Field'
import { InfoTip } from '@/components/InfoTip'
import { Section } from '@/components/Section'
import { Button } from '@/components/ui/button'
import { inr, inrShort } from '@/lib/money'
import { formatPercent, toneOf } from '@/lib/percent'
import { rangeStart, usefulRanges, type RangeKey } from '@/lib/ranges'
import { cn } from '@/lib/utils'

const axisMoney = (value: number) => inrShort(value.toFixed(0))

/** What my funds were worth over time, against what they cost and the same money in the
 * benchmark. The range's gain and return are the API's, worked out on every date. */
export function ValueChart({ portfolio }: { portfolio: Portfolio }) {
  const bucket = portfolio.bucket?.id
  const first = portfolio.returns?.since ?? null
  const last = portfolio.returns?.on ?? null
  const [range, setRange] = useState<RangeKey>('MAX')
  const start = last && range !== 'MAX' ? (rangeStart(range, last) ?? undefined) : undefined
  const history = usePortfolioHistory(start, !!last, bucket)
  const data = history.data
  const benchmarkName = data?.benchmark_fund?.name ?? 'Benchmark'

  const series = useMemo<ChartSeries[]>(() => {
    const points = data?.points ?? []
    const lines: ChartSeries[] = [
      {
        name: 'Value',
        color: 'var(--chart-main)',
        points: points.map((p) => ({ date: p.date, value: p.value })),
      },
      {
        name: 'Invested',
        color: 'var(--chart-invested)',
        dashed: true,
        points: points.map((p) => ({ date: p.date, value: p.invested })),
      },
    ]
    if (points.some((p) => p.benchmark !== null)) {
      lines.push({
        name: benchmarkName,
        color: 'var(--chart-benchmark)',
        dashed: true,
        points: points.flatMap((p) =>
          p.benchmark === null ? [] : [{ date: p.date, value: p.benchmark }],
        ),
      })
    }
    return lines
  }, [data, benchmarkName])

  if (!first || !last) return null
  const change = data?.change
  const benchmarkChange = data?.benchmark_change
  return (
    <Section
      title="Value over time"
      actions={
        <div className="flex flex-wrap gap-1" role="group" aria-label="Chart range">
          {usefulRanges(first, last).map((option) => (
            <Button
              key={option.key}
              size="sm"
              variant={range === option.key ? 'secondary' : 'ghost'}
              aria-pressed={range === option.key}
              disabled={option.disabled}
              onClick={() => setRange(option.key)}
              className="h-7 px-2 text-xs"
            >
              {option.label}
            </Button>
          ))}
        </div>
      }
    >
      <ErrorText error={history.error} />
      {change && (
        <dl className="flex flex-wrap gap-x-6 gap-y-1 text-sm" aria-label="Over this range">
          <Figure label="Gain" value={inr(change.gain)} tone={toneOf(change.gain)} />
          <Figure
            label="Return"
            value={formatPercent(change.return_pct)}
            tone={toneOf(change.return_pct)}
            info={
              <InfoTip label="Return">
                Time-weighted: how the funds moved, whenever money went in or out.
              </InfoTip>
            }
          />
          {benchmarkChange && (
            <Figure
              label={benchmarkName}
              value={formatPercent(benchmarkChange.return_pct)}
              tone={toneOf(benchmarkChange.return_pct)}
            />
          )}
        </dl>
      )}
      <LineChart
        label="Portfolio value over time"
        area
        height={260}
        series={series}
        formatValue={inr}
        formatAxis={axisMoney}
      />
    </Section>
  )
}

function Figure({
  label,
  value,
  tone,
  info,
}: {
  label: string
  value: string
  tone?: 'positive' | 'negative'
  info?: ReactNode
}) {
  return (
    <div className="flex min-w-0 items-baseline gap-1.5">
      <dt className="text-muted-foreground flex max-w-64 items-center gap-1 truncate text-xs">
        {label}
        {info}
      </dt>
      <dd
        className={cn(
          'font-semibold tabular-nums',
          tone === 'positive' && 'text-positive',
          tone === 'negative' && 'text-destructive',
        )}
      >
        {value}
      </dd>
    </div>
  )
}
