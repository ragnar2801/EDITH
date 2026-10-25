import { X } from 'lucide-react'
import { useMemo, useState } from 'react'

import { useBacktestInterval, type BacktestRun } from '@/api/queries'
import {
  LineChart,
  type ChartMarker,
  type ChartSelection,
  type ChartSeries,
} from '@/components/charts/LineChart'
import { Stat, StatGrid } from '@/components/Stat'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { inr, inrShort, formatNav } from '@/lib/money'
import { formatPercent, toneOf } from '@/lib/percent'
import { RANGES, rangeStart, usefulRanges, type RangeKey } from '@/lib/ranges'
import { formatDate } from '@/lib/time'

const axisMoney = (value: number) => inrShort(value.toFixed(0))

/** Everything a run returned (T1-14): figures vs the benchmark, chart, interval, tables. */
export function BacktestResults({ run }: { run: BacktestRun }) {
  const { result } = run
  const m = result.metrics
  const b = result.benchmark?.metrics
  const curve = result.curve
  const first = curve[0].date
  const last = curve[curve.length - 1].date
  const [range, setRange] = useState<RangeKey>('MAX')
  const [brush, setBrush] = useState<ChartSelection | null>(null)

  const cutoff = range === 'MAX' ? null : rangeStart(range, last)
  const visible = cutoff && cutoff > first ? cutoff : null
  const window: { start: string; end: string; label: string } | null = brush
    ? { ...brush, label: 'Selected' }
    : visible
      ? { start: visible, end: last, label: RANGES.find((r) => r.key === range)!.label }
      : null
  const interval = useBacktestInterval(run.id, window && { start: window.start, end: window.end })

  const series = useMemo<ChartSeries[]>(() => {
    const clip = <T extends { date: string }>(points: T[]) =>
      visible ? points.filter((point) => point.date >= visible) : points
    const lines: ChartSeries[] = [
      {
        name: run.bucket_name,
        color: 'var(--chart-main)',
        points: clip(curve).map((point) => ({ date: point.date, value: point.value })),
      },
    ]
    if (result.strategy === 'sip') {
      lines.push({
        name: 'Invested',
        color: 'var(--chart-invested)',
        dashed: true,
        points: clip(curve).map((point) => ({ date: point.date, value: point.invested })),
      })
    }
    if (result.benchmark) {
      lines.push({
        name: result.benchmark.name,
        color: 'var(--chart-benchmark)',
        dashed: true,
        points: clip(result.benchmark.curve).map((p) => ({ date: p.date, value: p.value })),
      })
    }
    return lines
  }, [curve, result, run.bucket_name, visible])

  const markers: ChartMarker[] = result.trades
    .filter((trade) => !visible || trade.date >= visible)
    .map((trade) => ({ date: trade.date, side: trade.side }))
  const vs = (value: string | null | undefined, sign = true) =>
    result.benchmark ? `Benchmark: ${formatPercent(value, { sign })}` : undefined
  const flows = m.total_withdrawn !== '0.00' || result.strategy !== 'regular'

  return (
    <div className="flex min-w-0 flex-col gap-4">
      {result.warnings.map((warning) => (
        <p
          key={warning}
          role="status"
          className="rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm"
        >
          {warning}
        </p>
      ))}

      <StatGrid>
        <Stat
          label="Final value"
          value={inrShort(m.end_value)}
          hint={b ? `Benchmark: ${inrShort(b.end_value)}` : formatDate(m.end_date)}
        />
        {flows && <Stat label="Money put in" value={inrShort(m.total_invested)} />}
        {m.total_withdrawn !== '0.00' && (
          <Stat label="Money taken out" value={inrShort(m.total_withdrawn)} />
        )}
        <Stat
          label="XIRR"
          value={formatPercent(m.xirr_pct)}
          tone={toneOf(m.xirr_pct)}
          hint={vs(b?.xirr_pct)}
        />
        <Stat
          label="CAGR (time-weighted)"
          value={formatPercent(m.cagr_pct)}
          tone={toneOf(m.cagr_pct)}
          hint={vs(b?.cagr_pct)}
        />
        <Stat
          label="Absolute return"
          value={formatPercent(m.absolute_return_pct)}
          tone={toneOf(m.absolute_return_pct)}
          hint={vs(b?.absolute_return_pct)}
        />
        <Stat
          label="Max drawdown"
          value={`−${formatPercent(m.max_drawdown_pct, { sign: false })}`}
          tone="negative"
          hint={b ? `Benchmark: −${formatPercent(b.max_drawdown_pct, { sign: false })}` : undefined}
        />
        <Stat
          label="Volatility"
          value={formatPercent(m.volatility_pct, { sign: false })}
          hint={vs(b?.volatility_pct, false)}
        />
        <Stat
          label="Sharpe"
          value={m.sharpe ?? '—'}
          hint={b ? `Benchmark: ${b.sharpe ?? '—'}` : undefined}
        />
        {result.strategy === 'swp' && (
          <Stat
            label="Money lasted?"
            value={m.depletion_date ? 'Ran out' : 'Yes'}
            tone={m.depletion_date ? 'negative' : 'positive'}
            hint={m.depletion_date ? formatDate(m.depletion_date) : `to ${formatDate(m.end_date)}`}
          />
        )}
      </StatGrid>
      <p className="text-muted-foreground text-xs">
        {formatDate(m.start_date)} to {formatDate(m.end_date)} ({m.years} years).
        {result.benchmark &&
          ` The benchmark line is the same money, on the same dates, in ${result.benchmark.name}.`}{' '}
        CAGR and drawdown measure the funds themselves; XIRR measures your actual cash flows.
      </p>

      <Card>
        <CardContent className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-muted-foreground mr-auto text-xs">
              Drag across the chart to measure a window
            </span>
            <div className="flex flex-wrap gap-1" role="group" aria-label="Chart range">
              {usefulRanges(first, last).map((option) => (
                <Button
                  key={option.key}
                  size="sm"
                  variant={range === option.key ? 'secondary' : 'ghost'}
                  aria-pressed={range === option.key}
                  disabled={option.disabled}
                  className="h-7 px-2 text-xs"
                  onClick={() => {
                    setRange(option.key)
                    setBrush(null)
                  }}
                >
                  {option.label}
                </Button>
              ))}
            </div>
          </div>
          <LineChart
            label="Backtest value over time"
            series={series}
            area
            height={320}
            formatValue={inr}
            formatAxis={axisMoney}
            selectable
            selection={brush}
            onSelectionChange={setBrush}
            markers={markers}
          />
          {window && (
            <div className="border-t pt-3" aria-live="polite">
              <div className="mb-2 flex items-center gap-2">
                <Badge variant="outline">{window.label}</Badge>
                <span className="text-muted-foreground text-xs">
                  {interval.data
                    ? `${formatDate(interval.data.start_date)} to ${formatDate(interval.data.end_date)}`
                    : '…'}
                </span>
                <Button
                  size="icon"
                  variant="ghost"
                  className="ml-auto size-7"
                  aria-label="Clear the window"
                  onClick={() => {
                    setBrush(null)
                    setRange('MAX')
                  }}
                >
                  <X />
                </Button>
              </div>
              {interval.isError && (
                <p className="text-destructive text-sm">{interval.error.message}</p>
              )}
              {interval.data && (
                <StatGrid>
                  <Stat
                    label="Return in window"
                    value={formatPercent(interval.data.return_pct)}
                    tone={toneOf(interval.data.return_pct)}
                    hint={
                      result.benchmark
                        ? `Benchmark: ${formatPercent(interval.data.benchmark_return_pct)}`
                        : undefined
                    }
                  />
                  <Stat
                    label="Max drawdown in window"
                    value={`−${formatPercent(interval.data.max_drawdown_pct, { sign: false })}`}
                    tone="negative"
                  />
                  <Stat label="Value at start" value={inrShort(interval.data.start_value)} />
                  <Stat label="Value at end" value={inrShort(interval.data.end_value)} />
                  {interval.data.invested !== '0.00' && (
                    <Stat label="Put in during window" value={inrShort(interval.data.invested)} />
                  )}
                  {interval.data.withdrawn !== '0.00' && (
                    <Stat
                      label="Taken out during window"
                      value={inrShort(interval.data.withdrawn)}
                    />
                  )}
                </StatGrid>
              )}
              <p className="text-muted-foreground mt-2 text-xs">
                Money-weighted return over the window (Modified Dietz): money put in or taken out
                isn’t counted as gain. A slice of this run, not a new one.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {result.strategy === 'custom' ? <CustomTables run={run} /> : <EndHoldings run={run} />}
    </div>
  )
}

function EndHoldings({ run }: { run: BacktestRun }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Funds at the end</CardTitle>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-muted-foreground text-left text-xs">
            <tr className="border-b">
              <th className="py-2 pr-3 font-medium">Fund</th>
              <th className="py-2 pr-3 text-right font-medium">Weight</th>
              <th className="py-2 pr-3 text-right font-medium">Units</th>
              <th className="py-2 text-right font-medium">Value</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {run.result.funds.map((fund) => (
              <tr key={fund.instrument_id}>
                <td className="py-2 pr-3">{fund.name}</td>
                <td className="py-2 pr-3 text-right tabular-nums">{fund.weight}%</td>
                <td className="py-2 pr-3 text-right tabular-nums">{fund.units}</td>
                <td className="py-2 text-right tabular-nums">{inr(fund.end_value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  )
}

function CustomTables({ run }: { run: BacktestRun }) {
  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Profit and loss per fund</CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full min-w-[32rem] text-sm">
            <thead className="text-muted-foreground text-left text-xs">
              <tr className="border-b">
                <th className="py-2 pr-3 font-medium">Fund</th>
                <th className="py-2 pr-3 text-right font-medium">Bought</th>
                <th className="py-2 pr-3 text-right font-medium">Sold</th>
                <th className="py-2 pr-3 text-right font-medium">Value at end</th>
                <th className="py-2 pr-3 text-right font-medium">P&amp;L</th>
                <th className="py-2 text-right font-medium">Return</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {run.result.funds.map((fund) => (
                <tr key={fund.instrument_id}>
                  <td className="py-2 pr-3">{fund.name}</td>
                  <td className="py-2 pr-3 text-right tabular-nums">{inr(fund.invested ?? '0')}</td>
                  <td className="py-2 pr-3 text-right tabular-nums">{inr(fund.proceeds ?? '0')}</td>
                  <td className="py-2 pr-3 text-right tabular-nums">{inr(fund.end_value)}</td>
                  <td
                    className={`py-2 pr-3 text-right tabular-nums ${toneOf(fund.pnl) === 'negative' ? 'text-destructive' : ''}`}
                  >
                    {fund.pnl ? inr(fund.pnl) : '—'}
                  </td>
                  <td className="py-2 text-right tabular-nums">{formatPercent(fund.pnl_pct)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Trades</CardTitle>
          <CardDescription>
            As executed, on the first NAV date on or after each date.
          </CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full min-w-[32rem] text-sm">
            <thead className="text-muted-foreground text-left text-xs">
              <tr className="border-b">
                <th className="py-2 pr-3 font-medium">Date</th>
                <th className="py-2 pr-3 font-medium">Side</th>
                <th className="py-2 pr-3 font-medium">Fund</th>
                <th className="py-2 pr-3 text-right font-medium">Units</th>
                <th className="py-2 pr-3 text-right font-medium">NAV</th>
                <th className="py-2 text-right font-medium">Amount</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {run.result.trades.map((trade, i) => (
                <tr key={i}>
                  <td className="py-2 pr-3 whitespace-nowrap">{formatDate(trade.date)}</td>
                  <td className="py-2 pr-3">
                    <Badge variant={trade.side === 'buy' ? 'outline' : 'secondary'}>
                      {trade.side}
                    </Badge>
                  </td>
                  <td className="py-2 pr-3">{trade.name}</td>
                  <td className="py-2 pr-3 text-right tabular-nums">{trade.units}</td>
                  <td className="py-2 pr-3 text-right tabular-nums">{formatNav(trade.nav)}</td>
                  <td className="py-2 text-right tabular-nums">{inr(trade.amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </>
  )
}
