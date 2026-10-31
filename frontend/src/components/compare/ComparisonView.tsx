import { useState, type ReactNode } from 'react'

import type { Schemas } from '@/api/client'
import { LineChart, type ChartSeries } from '@/components/charts/LineChart'
import { Swatch } from '@/components/compare/Swatch'
import { Table, TBody, Td, Th, THead, Tr } from '@/components/DataTable'
import { InfoTip } from '@/components/InfoTip'
import { Section } from '@/components/Section'
import { Segmented } from '@/components/Segmented'
import {
  BENCHMARK,
  ROLLING_YEARS,
  bestRows,
  seriesColor,
  type CompareKind,
  type Comparison,
  type Item,
} from '@/lib/compare'
import { inr, inrShort } from '@/lib/money'
import { formatPercent, toneClass } from '@/lib/percent'
import { cn } from '@/lib/utils'

type Row = {
  key: string
  item: Item
  /** Its id in correlation pairs. */
  id: number
  color: string
  benchmark: boolean
}
type Window = Schemas['WindowFiguresOut']
type Chart = 'growth' | 'drawdown' | 'rolling'
type Column = {
  title: ReactNode
  value: (row: Row) => string | number | null | undefined
  show: (row: Row) => ReactNode
  tone?: boolean
  lower?: boolean
  rank?: boolean
}

const CHARTS: Record<Chart, string> = {
  growth: 'Growth',
  drawdown: 'Drawdown',
  rolling: 'Rolling return',
}
const NOUNS: Record<CompareKind, string> = { funds: 'Fund', buckets: 'Bucket', models: 'Model' }
const GROWTH: Record<CompareKind, string> = {
  funds: '₹10,000 put in each fund on the first date compared.',
  buckets: '₹10,000 growing as each bucket did from the first date compared.',
  models: "₹10,000 split by each model's weights on the first date compared.",
}
const axisMoney = (value: number) => inrShort(value.toFixed(0))
const axisPercent = (value: number) => `${value.toFixed(0)}%`
const plain = (value: string | null | undefined) => formatPercent(value, { sign: false })
const signed = (value: string | null | undefined) => formatPercent(value)
const DAYS = new Intl.NumberFormat('en-IN')

function rowsOf(comparison: Comparison): Row[] {
  const rows: Row[] = comparison.items.map((item, index) => ({
    key: `item-${item.id}`,
    item,
    id: item.id,
    color: seriesColor(index),
    benchmark: false,
  }))
  if (comparison.benchmark) {
    rows.push({
      key: 'benchmark',
      item: comparison.benchmark,
      id: BENCHMARK,
      color: 'var(--chart-benchmark)',
      benchmark: true,
    })
  }
  return rows
}

/** Funds, buckets or models side by side: curves, then one table per kind of figure. */
export function ComparisonView({
  kind,
  comparison,
  rolling,
  onRolling,
}: {
  kind: CompareKind
  comparison: Comparison
  rolling: number
  onRolling: (years: number) => void
}) {
  const rows = rowsOf(comparison)
  const noun = NOUNS[kind]
  // Too short for even the shortest rolling period: nothing to pick between.
  const noRolling =
    rolling === ROLLING_YEARS[0] && rows.every((row) => !row.item.data.window?.rolling)
  return (
    <div className="flex flex-col gap-8">
      {comparison.window && <Curves kind={kind} rows={rows} />}
      {kind === 'buckets' && <Money rows={rows} />}
      <Returns noun={noun} rows={rows} sip={kind !== 'buckets'} />
      {comparison.window && (
        <>
          {!noRolling && (
            <RollingReturns
              noun={noun}
              rows={rows}
              years={rolling}
              windowYears={Number(comparison.window.years)}
              onYears={onRolling}
            />
          )}
          <Risk noun={noun} rows={rows} />
        </>
      )}
      <CalendarYears noun={noun} rows={rows} years={comparison.calendar_years} />
      {comparison.correlation.length > 0 && (
        <Correlations noun={noun} rows={rows} correlation={comparison.correlation} />
      )}
    </div>
  )
}

function Curves({ kind, rows }: { kind: CompareKind; rows: Row[] }) {
  const [chart, setChart] = useState<Chart>('growth')
  const points = (window: Window) =>
    chart === 'growth'
      ? window.growth
      : chart === 'drawdown'
        ? window.drawdown
        : (window.rolling?.curve ?? [])
  const series: ChartSeries[] = rows
    .filter((row) => row.item.data.window)
    .map((row) => ({
      name: row.benchmark ? `${row.item.name} (benchmark)` : row.item.name,
      color: row.color,
      dashed: row.benchmark,
      points: points(row.item.data.window!),
    }))

  return (
    <Section
      title={CHARTS[chart]}
      info={
        <InfoTip label={CHARTS[chart]}>
          {chart === 'growth'
            ? GROWTH[kind]
            : chart === 'drawdown'
              ? 'How far each was below its highest value so far.'
              : 'Yearly return over the rolling period ending on each date.'}
        </InfoTip>
      }
      actions={<Segmented label="Chart" value={chart} options={CHARTS} onChange={setChart} />}
    >
      <LineChart
        label={`${CHARTS[chart]} of the ${kind} compared`}
        series={series}
        formatValue={chart === 'growth' ? inr : signed}
        formatAxis={chart === 'growth' ? axisMoney : axisPercent}
      />
    </Section>
  )
}

/** The name with its colour; a click on the row opens it. */
function NameCell({ row }: { row: Row }) {
  return (
    <Td>
      <span className="flex items-center gap-2">
        <Swatch color={row.color} dashed={row.benchmark} />
        <span className="flex min-w-0 flex-col">
          <span className="truncate font-medium">{row.item.name}</span>
          {row.item.detail && (
            <span className="text-muted-foreground truncate text-xs">{row.item.detail}</span>
          )}
        </span>
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

/** A table with one row per pick, the benchmark last. Bold marks the best in a column. */
function FigureTable({
  label,
  noun,
  rows,
  columns,
}: {
  label: string
  noun: string
  rows: Row[]
  columns: Column[]
}) {
  const picked = rows.filter((row) => !row.benchmark)
  const best = columns.map((column) =>
    column.rank === false ? new Set<number>() : bestRows(picked.map(column.value), column),
  )
  return (
    <Table label={label}>
      <THead>
        <Th>{noun}</Th>
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
            to={row.item.to}
            className={cn(row.benchmark && 'text-muted-foreground')}
          >
            <NameCell row={row} />
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

/** What the money in each bucket made, as Portfolio shows it. */
function Money({ rows }: { rows: Row[] }) {
  const money = (row: Row) => row.item.money
  const amount = (pick: (m: NonNullable<Item['money']>) => string) => (row: Row) => {
    const m = money(row)
    return m ? inr(pick(m)) : '—'
  }
  return (
    <Section title="Money">
      <FigureTable
        label="Money"
        noun="Bucket"
        rows={rows.filter((row) => !row.benchmark)}
        columns={[
          {
            title: 'Invested',
            value: (row) => money(row)?.invested,
            show: amount((m) => m.invested),
            rank: false,
          },
          {
            title: 'Value',
            value: (row) => money(row)?.value,
            show: amount((m) => m.value),
            rank: false,
          },
          {
            title: 'Gain',
            value: (row) => money(row)?.gain,
            show: amount((m) => m.gain),
            tone: true,
            rank: false,
          },
          {
            title: 'Return',
            value: (row) => money(row)?.return_pct,
            show: (row) => signed(money(row)?.return_pct),
            tone: true,
          },
          {
            title: (
              <Heading
                text="XIRR"
                info="Yearly return on the money as it went in and out, shown after a year."
              />
            ),
            value: (row) => money(row)?.xirr_pct,
            show: (row) => signed(money(row)?.xirr_pct),
            tone: true,
          },
        ]}
      />
    </Section>
  )
}

function Returns({ noun, rows, sip }: { noun: string; rows: Row[]; sip: boolean }) {
  const w = (row: Row) => row.item.data.window
  const trailing = (['y1', 'y3', 'y5', 'y10'] as const).filter((key) =>
    rows.some((row) => row.item.data.trailing[key] !== null),
  )
  const sipColumns: Column[] = [
    {
      title: (
        <Heading
          text="SIP XIRR"
          info="₹10,000 on the first NAV date of every month over the dates compared."
        />
      ),
      value: (row) => w(row)?.sip.xirr_pct,
      show: (row) => signed(w(row)?.sip.xirr_pct),
      tone: true,
    },
    {
      title: 'SIP value',
      value: (row) => w(row)?.sip.value,
      show: (row) => (w(row) ? inr(w(row)!.sip.value) : '—'),
      rank: false,
    },
  ]
  return (
    <Section
      title="Returns"
      info={<InfoTip label="Returns">Yearly growth up to the same date for each.</InfoTip>}
    >
      <FigureTable
        label="Returns"
        noun={noun}
        rows={rows}
        columns={[
          ...trailing.map((key) => ({
            title: `${key.slice(1)}y`,
            value: (row: Row) => row.item.data.trailing[key],
            show: (row: Row) => signed(row.item.data.trailing[key]),
            tone: true,
          })),
          {
            title: <Heading text="Since start" info="Yearly growth over the dates compared." />,
            value: (row) => w(row)?.cagr_pct,
            show: (row) => signed(w(row)?.cagr_pct),
            tone: true,
          },
          ...(sip ? sipColumns : []),
        ]}
      />
    </Section>
  )
}

function RollingReturns({
  noun,
  rows,
  years,
  windowYears,
  onYears,
}: {
  noun: string
  rows: Row[]
  years: number
  windowYears: number
  onYears: (years: number) => void
}) {
  const options = Object.fromEntries(ROLLING_YEARS.map((y) => [String(y), `${y}y`])) as Record<
    string,
    string
  >
  const roll = (row: Row) => row.item.data.window?.rolling
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
      <FigureTable
        label="Rolling returns"
        noun={noun}
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
                info="Share of these stretches with a better return than the benchmark."
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

function Risk({ noun, rows }: { noun: string; rows: Row[] }) {
  const w = (row: Row) => row.item.data.window
  return (
    <Section title="Risk">
      <FigureTable
        label="Risk"
        noun={noun}
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
                info="Days from the peak before the largest drop until it was back there."
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
                info="How much of the benchmark's rise it caught in months the benchmark rose."
              />
            ),
            value: (row) => w(row)?.upside_capture_pct,
            show: (row) => (row.benchmark ? '' : plain(w(row)?.upside_capture_pct)),
          },
          {
            title: (
              <Heading
                text="Down capture"
                info="How much of the benchmark's fall it took in months the benchmark fell."
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

function CalendarYears({ noun, rows, years }: { noun: string; rows: Row[]; years: number[] }) {
  if (years.length === 0) return null
  const current = years[years.length - 1]
  const of = (row: Row, year: number) =>
    row.item.data.calendar.find((entry) => entry.year === year)?.return_pct ?? null
  const shown = years.filter((year) => rows.some((row) => of(row, year) !== null))
  if (shown.length === 0) return null
  return (
    <Section title="Calendar years">
      <FigureTable
        label="Calendar years"
        noun={noun}
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
  noun,
  rows,
  correlation,
}: {
  noun: string
  rows: Row[]
  correlation: Comparison['correlation']
}) {
  const ids = new Set(correlation.flatMap((pair) => [pair.a, pair.b]))
  const shown = rows.filter((row) => ids.has(row.id))
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
          How closely weekly returns moved together: near 1 means they behave alike.
        </InfoTip>
      }
    >
      <Table label="Correlation">
        <THead>
          <Th>{noun}</Th>
          {shown.map((row) => (
            <Th key={row.key} numeric>
              <span className="inline-flex" title={row.item.name}>
                <Swatch color={row.color} dashed={row.benchmark} />
                <span className="sr-only">{row.item.name}</span>
              </span>
            </Th>
          ))}
        </THead>
        <TBody>
          {shown.map((row) => (
            <Tr key={row.key} className={cn(row.benchmark && 'text-muted-foreground')}>
              <NameCell row={row} />
              {shown.map((other) => {
                const figure = value(row.id, other.id)
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
