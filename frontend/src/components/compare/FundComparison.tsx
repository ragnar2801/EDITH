import { useState, type ReactNode } from 'react'

import type { Schemas } from '@/api/client'
import { LineChart, type ChartSeries } from '@/components/charts/LineChart'
import { Swatch } from '@/components/compare/Swatch'
import { Table, TBody, Td, Th, THead, Tr } from '@/components/DataTable'
import { InfoTip } from '@/components/InfoTip'
import { FundName } from '@/components/models/FundName'
import { Section } from '@/components/Section'
import { Segmented } from '@/components/Segmented'
import {
  ROLLING_YEARS,
  bestRows,
  seriesColor,
  type ComparedFund,
  type Comparison,
} from '@/lib/compare'
import { fundPath } from '@/lib/instruments'
import { inr, inrShort } from '@/lib/money'
import { formatPercent, toneClass } from '@/lib/percent'
import { cn } from '@/lib/utils'

type Row = {
  key: string
  data: ComparedFund
  color: string
  benchmark: boolean
}
type Window = Schemas['WindowFiguresOut']
type Chart = 'growth' | 'drawdown' | 'rolling'

const CHARTS: Record<Chart, string> = {
  growth: 'Growth',
  drawdown: 'Drawdown',
  rolling: 'Rolling return',
}
const axisMoney = (value: number) => inrShort(value.toFixed(0))
const axisPercent = (value: number) => `${value.toFixed(0)}%`
const plain = (value: string | null | undefined) => formatPercent(value, { sign: false })
const signed = (value: string | null | undefined) => formatPercent(value)
const DAYS = new Intl.NumberFormat('en-IN')

function rowsOf(comparison: Comparison): Row[] {
  const rows: Row[] = comparison.funds.map((data, index) => ({
    key: `fund-${data.fund.id}`,
    data,
    color: seriesColor(index),
    benchmark: false,
  }))
  if (comparison.benchmark) {
    rows.push({
      key: 'benchmark',
      data: comparison.benchmark,
      color: 'var(--chart-benchmark)',
      benchmark: true,
    })
  }
  return rows
}

export function FundComparison({
  comparison,
  rolling,
  onRolling,
}: {
  comparison: Comparison
  rolling: number
  onRolling: (years: number) => void
}) {
  const rows = rowsOf(comparison)
  return (
    <div className="flex flex-col gap-8">
      {comparison.window && <Curves rows={rows} />}
      <Returns rows={rows} />
      {comparison.window && (
        <>
          <RollingReturns
            rows={rows}
            years={rolling}
            windowYears={Number(comparison.window.years)}
            onYears={onRolling}
          />
          <Risk rows={rows} />
        </>
      )}
      <CalendarYears rows={rows} years={comparison.calendar_years} />
      {comparison.correlation.length > 0 && (
        <Correlations rows={rows} correlation={comparison.correlation} />
      )}
    </div>
  )
}

function Curves({ rows }: { rows: Row[] }) {
  const [chart, setChart] = useState<Chart>('growth')
  const points = (window: Window) =>
    chart === 'growth'
      ? window.growth
      : chart === 'drawdown'
        ? window.drawdown
        : (window.rolling?.curve ?? [])
  const series: ChartSeries[] = rows
    .filter((row) => row.data.window)
    .map((row) => ({
      name: row.benchmark ? `${row.data.fund.name} (benchmark)` : row.data.fund.name,
      color: row.color,
      dashed: row.benchmark,
      points: points(row.data.window!),
    }))

  return (
    <Section
      title={CHARTS[chart]}
      info={
        <InfoTip label={CHARTS[chart]}>
          {chart === 'growth'
            ? '₹10,000 put in each fund on the first date compared.'
            : chart === 'drawdown'
              ? 'How far each fund was below its highest value so far.'
              : 'Yearly return over the rolling period ending on each date.'}
        </InfoTip>
      }
      actions={<Segmented label="Chart" value={chart} options={CHARTS} onChange={setChart} />}
    >
      <LineChart
        label={`${CHARTS[chart]} of the funds compared`}
        series={series}
        formatValue={chart === 'growth' ? inr : signed}
        formatAxis={chart === 'growth' ? axisMoney : axisPercent}
      />
    </Section>
  )
}

/** The fund's name with its colour; a click opens the fund. */
function FundCell({ row }: { row: Row }) {
  return (
    <Td>
      <span className="flex items-center gap-2">
        <Swatch color={row.color} dashed={row.benchmark} />
        <FundName fund={row.data.fund} />
      </span>
    </Td>
  )
}

function Figure({
  best,
  className,
  children,
}: {
  best?: boolean
  className?: string
  children: ReactNode
}) {
  return (
    <Td numeric className={cn(best && 'font-semibold', className)}>
      {children}
    </Td>
  )
}

/** A table with one row per fund, the benchmark last. Bold marks the best in a column. */
function FundTable({
  label,
  rows,
  columns,
}: {
  label: string
  rows: Row[]
  columns: {
    title: ReactNode
    value: (row: Row) => string | number | null | undefined
    show: (row: Row) => ReactNode
    tone?: boolean
    lower?: boolean
    rank?: boolean
  }[]
}) {
  const funds = rows.filter((row) => !row.benchmark)
  const best = columns.map((column) =>
    column.rank === false ? new Set<number>() : bestRows(funds.map(column.value), column),
  )
  return (
    <Table label={label}>
      <THead>
        <Th>Fund</Th>
        {columns.map((column, i) => (
          <Th key={i} numeric>
            {column.title}
          </Th>
        ))}
      </THead>
      <TBody>
        {rows.map((row, r) => (
          <Tr
            key={row.key}
            to={fundPath(row.data.fund.id)}
            className={cn(row.benchmark && 'text-muted-foreground')}
          >
            <FundCell row={row} />
            {columns.map((column, i) => {
              const value = column.value(row)
              return (
                <Figure
                  key={i}
                  best={!row.benchmark && best[i].has(r)}
                  className={
                    column.tone && typeof value === 'string' ? toneClass(value) : undefined
                  }
                >
                  {column.show(row)}
                </Figure>
              )
            })}
          </Tr>
        ))}
      </TBody>
    </Table>
  )
}

function Heading({ text, info }: { text: string; info: string }) {
  return (
    <span className="inline-flex items-center gap-1">
      {text}
      <InfoTip label={text}>{info}</InfoTip>
    </span>
  )
}

function Returns({ rows }: { rows: Row[] }) {
  const trailing = (['y1', 'y3', 'y5', 'y10'] as const).filter((key) =>
    rows.some((row) => row.data.trailing[key] !== null),
  )
  return (
    <Section
      title="Returns"
      info={<InfoTip label="Returns">Yearly growth up to the same date for every fund.</InfoTip>}
    >
      <FundTable
        label="Returns"
        rows={rows}
        columns={[
          ...trailing.map((key) => ({
            title: `${key.slice(1)}y`,
            value: (row: Row) => row.data.trailing[key],
            show: (row: Row) => signed(row.data.trailing[key]),
            tone: true,
          })),
          {
            title: <Heading text="Since start" info="Yearly growth over the dates compared." />,
            value: (row) => row.data.window?.cagr_pct,
            show: (row) => signed(row.data.window?.cagr_pct),
            tone: true,
          },
          {
            title: (
              <Heading
                text="SIP XIRR"
                info="₹10,000 on the first NAV date of every month over the dates compared."
              />
            ),
            value: (row) => row.data.window?.sip.xirr_pct,
            show: (row) => signed(row.data.window?.sip.xirr_pct),
            tone: true,
          },
          {
            title: 'SIP value',
            value: (row) => row.data.window?.sip.value,
            show: (row) => (row.data.window ? inr(row.data.window.sip.value) : '—'),
            rank: false,
          },
        ]}
      />
    </Section>
  )
}

function RollingReturns({
  rows,
  years,
  windowYears,
  onYears,
}: {
  rows: Row[]
  years: number
  windowYears: number
  onYears: (years: number) => void
}) {
  const options = Object.fromEntries(ROLLING_YEARS.map((y) => [String(y), `${y}y`])) as Record<
    string,
    string
  >
  const roll = (row: Row) => row.data.window?.rolling
  return (
    <Section
      title="Rolling returns"
      info={
        <InfoTip label="Rolling returns">
          Yearly return over every {years}-year stretch inside the dates compared, one ending on
          each day.
        </InfoTip>
      }
      actions={
        <Segmented
          label="Rolling period"
          value={String(years)}
          options={options}
          disabled={ROLLING_YEARS.filter((y) => y > windowYears).map(String)}
          onChange={(value) => onYears(Number(value))}
        />
      }
    >
      <FundTable
        label="Rolling returns"
        rows={rows}
        columns={[
          {
            title: 'Median',
            value: (row) => roll(row)?.median_pct,
            show: (row) => signed(roll(row)?.median_pct),
            tone: true,
          },
          {
            title: 'Worst',
            value: (row) => roll(row)?.worst_pct,
            show: (row) => signed(roll(row)?.worst_pct),
            tone: true,
          },
          {
            title: 'Best',
            value: (row) => roll(row)?.best_pct,
            show: (row) => signed(roll(row)?.best_pct),
            tone: true,
          },
          {
            title: (
              <Heading
                text="Beat benchmark"
                info="Share of these stretches in which the fund did better than the benchmark."
              />
            ),
            value: (row) => roll(row)?.beat_benchmark_pct,
            show: (row) => (row.benchmark ? '' : plain(roll(row)?.beat_benchmark_pct)),
          },
        ]}
      />
    </Section>
  )
}

function recovery(window: Window | null | undefined): string {
  if (!window || window.recovery_days === null) return '—'
  const days = `${DAYS.format(window.recovery_days)} days`
  return window.recovered ? days : `Not yet (${days})`
}

function Risk({ rows }: { rows: Row[] }) {
  const w = (row: Row) => row.data.window
  return (
    <Section title="Risk">
      <FundTable
        label="Risk"
        rows={rows}
        columns={[
          {
            title: (
              <Heading text="Volatility" info="How much daily returns swing, as a yearly figure." />
            ),
            value: (row) => w(row)?.volatility_pct,
            show: (row) => plain(w(row)?.volatility_pct),
            lower: true,
          },
          {
            title: 'Max drop',
            value: (row) => w(row)?.max_drawdown_pct,
            show: (row) => plain(w(row)?.max_drawdown_pct),
            lower: true,
          },
          {
            title: (
              <Heading
                text="Recovery"
                info="Days from the peak before the largest drop until the fund was back at it."
              />
            ),
            value: (row) => (w(row)?.recovered ? w(row)?.recovery_days : null),
            show: (row) => recovery(w(row)),
            lower: true,
          },
          {
            title: <Heading text="Calmar" info="Yearly growth divided by the largest drop." />,
            value: (row) => w(row)?.calmar,
            show: (row) => w(row)?.calmar ?? '—',
          },
          {
            title: (
              <Heading
                text="Up capture"
                info="How much of the benchmark's rise the fund caught in months the benchmark rose."
              />
            ),
            value: (row) => w(row)?.upside_capture_pct,
            show: (row) => (row.benchmark ? '' : plain(w(row)?.upside_capture_pct)),
          },
          {
            title: (
              <Heading
                text="Down capture"
                info="How much of the benchmark's fall the fund took in months the benchmark fell."
              />
            ),
            value: (row) => w(row)?.downside_capture_pct,
            show: (row) => (row.benchmark ? '' : plain(w(row)?.downside_capture_pct)),
            lower: true,
          },
        ]}
      />
    </Section>
  )
}

function CalendarYears({ rows, years }: { rows: Row[]; years: number[] }) {
  if (years.length === 0) return null
  const current = years[years.length - 1]
  const of = (row: Row, year: number) =>
    row.data.calendar.find((entry) => entry.year === year)?.return_pct ?? null
  const shown = years.filter((year) => rows.some((row) => of(row, year) !== null))
  if (shown.length === 0) return null
  return (
    <Section title="Calendar years">
      <FundTable
        label="Calendar years"
        rows={rows}
        columns={shown.map((year) => ({
          title: year === current ? `${year} YTD` : String(year),
          value: (row: Row) => of(row, year),
          show: (row: Row) => signed(of(row, year)),
          tone: true,
        }))}
      />
    </Section>
  )
}

function Correlations({
  rows,
  correlation,
}: {
  rows: Row[]
  correlation: Comparison['correlation']
}) {
  const ids = new Set(correlation.flatMap((pair) => [pair.a, pair.b]))
  // A fund picked as its own benchmark appears once.
  const shown = rows.filter(
    (row, i) =>
      ids.has(row.data.fund.id) &&
      rows.findIndex((other) => other.data.fund.id === row.data.fund.id) === i,
  )
  const value = (a: number, b: number) =>
    a === b
      ? '1.00'
      : (correlation.find(
          (pair) => (pair.a === a && pair.b === b) || (pair.a === b && pair.b === a),
        )?.value ?? null)

  return (
    <Section
      title="Correlation"
      info={
        <InfoTip label="Correlation">
          How closely weekly returns moved together: near 1 means the funds behave alike.
        </InfoTip>
      }
    >
      <Table label="Correlation">
        <THead>
          <Th>Fund</Th>
          {shown.map((row) => (
            <Th key={row.key} numeric>
              <span className="inline-flex" title={row.data.fund.name}>
                <Swatch color={row.color} dashed={row.benchmark} />
                <span className="sr-only">{row.data.fund.name}</span>
              </span>
            </Th>
          ))}
        </THead>
        <TBody>
          {shown.map((row) => (
            <Tr key={row.key} className={cn(row.benchmark && 'text-muted-foreground')}>
              <FundCell row={row} />
              {shown.map((other) => {
                const figure = value(row.data.fund.id, other.data.fund.id)
                return (
                  <Td
                    key={other.key}
                    numeric
                    className={cn(
                      row === other && 'text-muted-foreground',
                      row !== other && figure !== null && Number(figure) >= 0.9 && 'font-semibold',
                    )}
                  >
                    {figure ?? '—'}
                  </Td>
                )
              })}
            </Tr>
          ))}
        </TBody>
      </Table>
    </Section>
  )
}
