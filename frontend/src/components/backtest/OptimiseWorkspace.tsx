import { ChevronDown, ChevronRight, Loader2, Sparkles } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router'

import { useOptimise, type Optimised } from '@/api/queries'
import { ScatterChart, type ScatterMark } from '@/components/charts/ScatterChart'
import { Table, TBody, Td, Th, THead, Tr } from '@/components/DataTable'
import { EmptyState } from '@/components/EmptyState'
import { ErrorText, Field } from '@/components/Field'
import { InfoTip } from '@/components/InfoTip'
import { Section } from '@/components/Section'
import { Segmented } from '@/components/Segmented'
import { Stat, StatGrid } from '@/components/Stat'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { NativeSelect } from '@/components/ui/native-select'
import { FREQUENCY_LABELS, type Frequency } from '@/lib/backtest'
import { REBALANCE_LABELS, type Bucket, type Rebalance } from '@/lib/buckets'
import { inrShort } from '@/lib/money'
import { backtestPath } from '@/lib/models'
import {
  DEFAULT_OPTIMISE,
  GOAL_LABELS,
  MAX_FUNDS,
  handoff,
  toRequest,
  type Candidate,
  type Goal,
  type OptimiseForm,
} from '@/lib/optimise'
import { formatPercent } from '@/lib/percent'
import { formatDate } from '@/lib/time'

const STRATEGIES = { regular: 'Lump sum', sip: 'SIP' } as const

/** Try every split of a model's funds and rank them: settings left, results right. */
export function OptimiseWorkspace({ bucket }: { bucket: Bucket }) {
  const [form, setForm] = useState(DEFAULT_OPTIMISE)
  const [asked, setAsked] = useState(DEFAULT_OPTIMISE)
  const optimise = useOptimise()

  if (bucket.funds.length > MAX_FUNDS) {
    return <EmptyState icon={Sparkles} title={`Optimise works with up to ${MAX_FUNDS} funds`} />
  }
  return (
    <div className="grid items-start gap-6 lg:grid-cols-[18rem_minmax(0,1fr)]">
      <Card className="lg:sticky lg:top-20">
        <CardContent className="flex flex-col gap-4">
          <Settings
            bucket={bucket}
            form={form}
            onForm={setForm}
            running={optimise.isPending}
            onRun={() => {
              setAsked(form)
              optimise.mutate(toRequest(form, bucket))
            }}
          />
          <ErrorText error={optimise.error} />
        </CardContent>
      </Card>
      {optimise.data ? (
        <Results bucket={bucket} form={asked} result={optimise.data} />
      ) : (
        <EmptyState icon={Sparkles} title={`Find the best split of ${bucket.name}`} />
      )}
    </div>
  )
}

function Settings({
  bucket,
  form,
  onForm,
  running,
  onRun,
}: {
  bucket: Bucket
  form: OptimiseForm
  onForm: (form: OptimiseForm) => void
  running: boolean
  onRun: () => void
}) {
  const [more, setMore] = useState(false)
  const set = (patch: Partial<OptimiseForm>) => onForm({ ...form, ...patch })
  const text = (key: keyof OptimiseForm, label: string, info?: string) => (
    <Field label={label} info={info} size="sm">
      {(id) => (
        <Input
          id={id}
          inputMode="decimal"
          value={form[key]}
          onChange={(event) => set({ [key]: event.target.value })}
        />
      )}
    </Field>
  )

  return (
    <form
      aria-label="Optimise settings"
      className="flex flex-col gap-4"
      onSubmit={(event) => {
        event.preventDefault()
        onRun()
      }}
    >
      <Segmented
        label="Strategy"
        value={form.strategy}
        options={STRATEGIES}
        onChange={(strategy) => set({ strategy })}
      />
      {form.strategy === 'regular' ? (
        <>
          {text('capital', 'Lump sum (₹)')}
          <Field label="Rebalance" size="sm">
            {(id) => (
              <NativeSelect
                id={id}
                value={form.rebalance}
                onChange={(event) => set({ rebalance: event.target.value as '' | Rebalance })}
              >
                <option value="">
                  Model’s own ({REBALANCE_LABELS[bucket.rebalance].toLowerCase()})
                </option>
                {(Object.keys(REBALANCE_LABELS) as Rebalance[]).map((key) => (
                  <option key={key} value={key}>
                    {REBALANCE_LABELS[key]}
                  </option>
                ))}
              </NativeSelect>
            )}
          </Field>
        </>
      ) : (
        <>
          {text('amount', 'SIP amount (₹)')}
          <Field label="Every" size="sm">
            {(id) => (
              <NativeSelect
                id={id}
                value={form.frequency}
                onChange={(event) => set({ frequency: event.target.value as Frequency })}
              >
                {(Object.keys(FREQUENCY_LABELS) as Frequency[]).map((key) => (
                  <option key={key} value={key}>
                    {FREQUENCY_LABELS[key]}
                  </option>
                ))}
              </NativeSelect>
            )}
          </Field>
        </>
      )}
      <Field label="Goal" size="sm">
        {(id) => (
          <NativeSelect
            id={id}
            value={form.goal}
            onChange={(event) => set({ goal: event.target.value as Goal })}
          >
            {(Object.keys(GOAL_LABELS) as Goal[]).map((key) => (
              <option key={key} value={key}>
                {GOAL_LABELS[key]}
              </option>
            ))}
          </NativeSelect>
        )}
      </Field>
      {text('maxDrawdown', 'Max drawdown (%)', 'Leave out splits that fell further.')}
      {text('minXirr', 'Min XIRR (%)', 'Leave out splits that earned less.')}
      <div className="grid gap-2">
        <Field label="From" info="Blank: from the first date every fund has a NAV." size="sm">
          {(id) => (
            <Input
              id={id}
              type="date"
              value={form.start}
              onChange={(event) => set({ start: event.target.value })}
            />
          )}
        </Field>
        <Field label="To" info="Blank: to the latest NAV." size="sm">
          {(id) => (
            <Input
              id={id}
              type="date"
              value={form.end}
              onChange={(event) => set({ end: event.target.value })}
            />
          )}
        </Field>
      </div>
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
        <>
          {text('step', 'Step (%)', 'Weights go up in steps of this; it must divide 100.')}
          {text('minWeight', 'Lowest weight (%)', '0 lets a fund drop out.')}
          {text('maxWeight', 'Highest weight (%)')}
          {text('riskFree', 'Risk-free rate (% a year)', 'Used for Sharpe.')}
        </>
      )}
      <Button type="submit" disabled={running}>
        {running && <Loader2 className="animate-spin" />}
        Find splits
      </Button>
    </form>
  )
}

const pct = (value: string | null | undefined) => formatPercent(value, { sign: false })

function Results({
  bucket,
  form,
  result,
}: {
  bucket: Bucket
  form: OptimiseForm
  result: Optimised
}) {
  const navigate = useNavigate()
  const best = result.top[0]
  const marks: ScatterMark[] = [
    point('Your model', 'var(--foreground)', result.model.metrics),
    ...(result.benchmark
      ? [point(result.benchmark.name, 'var(--chart-benchmark)', result.benchmark.metrics)]
      : []),
    ...(best ? [point('Best', 'var(--positive)', best.metrics)] : []),
  ]
  const tryIt = (candidate: Candidate) =>
    navigate(backtestPath(bucket.id), {
      state: handoff(form, candidate, bucket, result.start_date),
    })

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
        <Stat label="Splits tried" value={result.tried.toLocaleString('en-IN')} />
        <Stat label="Within limits" value={result.eligible.toLocaleString('en-IN')} />
        <Stat
          label="Period"
          value={formatDate(result.start_date)}
          hint={`to ${formatDate(result.end_date)}`}
        />
      </StatGrid>

      <Card>
        <CardContent>
          <ScatterChart
            label="Every split: XIRR against max drawdown"
            xLabel="Max drawdown (%)"
            yLabel="XIRR (%)"
            formatAxis={(value) => value.toFixed(0)}
            points={result.points.map((p) => ({
              x: p.max_drawdown_pct,
              y: p.xirr_pct ?? '',
              label: `XIRR ${pct(p.xirr_pct)} · drawdown ${pct(p.max_drawdown_pct)}`,
              muted: !p.eligible,
            }))}
            marks={marks}
          />
        </CardContent>
      </Card>

      <Section
        title={GOAL_LABELS[form.goal]}
        info={<InfoTip label="Figures">Each split re-run as a full backtest.</InfoTip>}
      >
        {result.top.length === 0 ? (
          <EmptyState icon={Sparkles} title="No split is within the limits" />
        ) : (
          <Table label="Best splits">
            <THead>
              <Th>Split</Th>
              <Th numeric>XIRR</Th>
              <Th numeric>CAGR</Th>
              <Th numeric>Max drawdown</Th>
              <Th numeric>Volatility</Th>
              <Th numeric>Sharpe</Th>
              <Th numeric>Final value</Th>
              <Th />
            </THead>
            <TBody>
              <Row candidate={result.model} label={<Badge variant="outline">Your model</Badge>} />
              {result.top.map((candidate, i) => (
                <Row key={i} candidate={candidate} onTry={() => tryIt(candidate)} />
              ))}
            </TBody>
          </Table>
        )}
      </Section>
    </div>
  )
}

function point(name: string, color: string, m: Candidate['metrics']): ScatterMark {
  return {
    name,
    color,
    x: m.max_drawdown_pct,
    y: m.xirr_pct ?? '',
    label: `${name}: XIRR ${pct(m.xirr_pct)} · drawdown ${pct(m.max_drawdown_pct)}`,
  }
}

function Row({
  candidate,
  label,
  onTry,
}: {
  candidate: Candidate
  label?: ReactNode
  onTry?: () => void
}) {
  const m = candidate.metrics
  return (
    <Tr>
      <Td>
        <div className="flex flex-col gap-0.5">
          {label}
          {candidate.funds.map((fund) => (
            <span key={fund.instrument_id} className="flex gap-2 text-xs">
              <span className="max-w-56 truncate">{fund.name}</span>
              <span className="text-muted-foreground ml-auto tabular-nums">{fund.weight}%</span>
            </span>
          ))}
        </div>
      </Td>
      <Td numeric>{formatPercent(m.xirr_pct)}</Td>
      <Td numeric>{formatPercent(m.cagr_pct)}</Td>
      <Td numeric>−{pct(m.max_drawdown_pct)}</Td>
      <Td numeric>{pct(m.volatility_pct)}</Td>
      <Td numeric>{m.sharpe ?? '—'}</Td>
      <Td numeric>{inrShort(m.end_value)}</Td>
      <Td>
        {onTry && (
          <Button size="sm" variant="outline" aria-label="Try this split" onClick={onTry}>
            Try
          </Button>
        )}
      </Td>
    </Tr>
  )
}
