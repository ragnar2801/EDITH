import { X } from 'lucide-react'
import { useMemo, useState } from 'react'

import { useBacktestInterval, type BacktestRun } from '@/api/queries'
import {
  LineChart,
  type ChartMarker,
  type ChartSelection,
  type ChartSeries,
} from '@/components/charts/LineChart'
import { Table, TBody, Td, Th, THead, Tr } from '@/components/DataTable'
import { ErrorText } from '@/components/Field'
import { InfoTip } from '@/components/InfoTip'
import { Section } from '@/components/Section'
import { Stat, StatGrid } from '@/components/Stat'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { inr, inrShort, formatNav } from '@/lib/money'
import { formatPercent, toneOf } from '@/lib/percent'
import { RANGES, rangeStart, usefulRanges, type RangeKey } from '@/lib/ranges'
import { formatDate } from '@/lib/time'

import { RunComparison } from './RunComparison'

const axisMoney = (value: number) => inrShort(value.toFixed(0))

/** One-line definitions for the figures. */
const METRIC_INFO = {
  xirr: 'Annual return on your actual cash flows, money-weighted.',
  cagr: 'Annual growth of the funds themselves, time-weighted; ignores when money went in.',
  absolute: 'Total gain as a share of the money put in.',
  drawdown: 'The largest fall from a peak before a new high.',
  volatility: 'How much daily returns swing, a year.',
  sharpe: 'Return above the risk-free rate per unit of volatility. Higher is better.',
  window: 'Money-weighted return over the window: money put in or taken out isn’t gain.',
}

const tip = (label: string, text: string) => <InfoTip label={label}>{text}</InfoTip>

/** Everything a run returned: figures vs the benchmark, chart, interval, tables, and
 * what changed against `baseline`, which is drawn faded. */
export function BacktestResults({
  run,
  baseline = null,
  onClearBaseline,
}: {
  run: BacktestRun
  baseline?: BacktestRun | null
  onClearBaseline?: () => void
}) {
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
        name: run.model_name,
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
    if (baseline) {
      lines.push({
        name: baseline.name ?? 'Previous run',
        color: 'color-mix(in oklch, var(--chart-main) 40%, transparent)',
        points: clip(baseline.result.curve).map((p) => ({ date: p.date, value: p.value })),
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
  }, [baseline, curve, result, run.model_name, visible])

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
          info={tip('XIRR', METRIC_INFO.xirr)}
          value={formatPercent(m.xirr_pct)}
          tone={toneOf(m.xirr_pct)}
          hint={vs(b?.xirr_pct)}
        />
        <Stat
          label="CAGR"
          info={tip('CAGR', METRIC_INFO.cagr)}
          value={formatPercent(m.cagr_pct)}
          tone={toneOf(m.cagr_pct)}
          hint={vs(b?.cagr_pct)}
        />
        <Stat
          label="Absolute return"
          info={tip('Absolute return', METRIC_INFO.absolute)}
          value={formatPercent(m.absolute_return_pct)}
          tone={toneOf(m.absolute_return_pct)}
          hint={vs(b?.absolute_return_pct)}
        />
        <Stat
          label="Max drawdown"
          info={tip('Max drawdown', METRIC_INFO.drawdown)}
          value={`−${formatPercent(m.max_drawdown_pct, { sign: false })}`}
          tone="negative"
          hint={b ? `Benchmark: −${formatPercent(b.max_drawdown_pct, { sign: false })}` : undefined}
        />
        <Stat
          label="Volatility"
          info={tip('Volatility', METRIC_INFO.volatility)}
          value={formatPercent(m.volatility_pct, { sign: false })}
          hint={vs(b?.volatility_pct, false)}
        />
        <Stat
          label="Sharpe"
          info={tip('Sharpe', METRIC_INFO.sharpe)}
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
        {formatDate(m.start_date)} – {formatDate(m.end_date)} · {m.years} years
        {result.benchmark && ` · vs ${result.benchmark.name}`}
      </p>

      {baseline && (
        <RunComparison run={run} baseline={baseline} onClear={() => onClearBaseline?.()} />
      )}

      <Card>
        <CardContent className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="mr-auto">
              <InfoTip label="Chart">Drag across the chart to measure a window.</InfoTip>
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
              <ErrorText error={interval.error} />
              {interval.data && (
                <StatGrid>
                  <Stat
                    label="Return in window"
                    info={tip('Return in window', METRIC_INFO.window)}
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
    <Section title="Funds at the end">
      <Table label="Funds at the end">
        <THead>
          <Th>Fund</Th>
          <Th numeric>Weight</Th>
          <Th numeric>Units</Th>
          <Th numeric>Value</Th>
        </THead>
        <TBody>
          {run.result.funds.map((fund) => (
            <Tr key={fund.instrument_id}>
              <Td>{fund.name}</Td>
              <Td numeric>{fund.weight}%</Td>
              <Td numeric>{fund.units}</Td>
              <Td numeric>{inr(fund.end_value)}</Td>
            </Tr>
          ))}
        </TBody>
      </Table>
    </Section>
  )
}

function CustomTables({ run }: { run: BacktestRun }) {
  return (
    <>
      <Section title="Profit and loss per fund">
        <Table label="Profit and loss per fund">
          <THead>
            <Th>Fund</Th>
            <Th numeric>Bought</Th>
            <Th numeric>Sold</Th>
            <Th numeric>Value at end</Th>
            <Th numeric>P&amp;L</Th>
            <Th numeric>Return</Th>
          </THead>
          <TBody>
            {run.result.funds.map((fund) => (
              <Tr key={fund.instrument_id}>
                <Td>{fund.name}</Td>
                <Td numeric>{inr(fund.invested ?? '0')}</Td>
                <Td numeric>{inr(fund.proceeds ?? '0')}</Td>
                <Td numeric>{inr(fund.end_value)}</Td>
                <Td
                  numeric
                  className={toneOf(fund.pnl) === 'negative' ? 'text-destructive' : undefined}
                >
                  {fund.pnl ? inr(fund.pnl) : '—'}
                </Td>
                <Td numeric>{formatPercent(fund.pnl_pct)}</Td>
              </Tr>
            ))}
          </TBody>
        </Table>
      </Section>
      <Section
        title="Trades"
        info={<InfoTip label="Trades">On the first NAV date on or after each date.</InfoTip>}
      >
        <Table label="Trades">
          <THead>
            <Th>Date</Th>
            <Th>Side</Th>
            <Th>Fund</Th>
            <Th numeric>Units</Th>
            <Th numeric>NAV</Th>
            <Th numeric>Amount</Th>
          </THead>
          <TBody>
            {run.result.trades.map((trade, i) => (
              <Tr key={i}>
                <Td className="whitespace-nowrap">{formatDate(trade.date)}</Td>
                <Td>
                  <Badge variant={trade.side === 'buy' ? 'outline' : 'secondary'}>
                    {trade.side === 'buy' ? 'Buy' : 'Sell'}
                  </Badge>
                </Td>
                <Td>{trade.name}</Td>
                <Td numeric>{trade.units}</Td>
                <Td numeric>{formatNav(trade.nav)}</Td>
                <Td numeric>{inr(trade.amount)}</Td>
              </Tr>
            ))}
          </TBody>
        </Table>
      </Section>
    </>
  )
}
