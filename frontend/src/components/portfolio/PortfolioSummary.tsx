import type { Portfolio } from '@/api/queries'
import { InfoTip } from '@/components/InfoTip'
import { Section } from '@/components/Section'
import { Stat, StatGrid } from '@/components/Stat'
import { inr } from '@/lib/money'
import { formatPercent, toneOf } from '@/lib/percent'
import { ASSET_LABELS } from '@/lib/portfolio'
import { formatDate, formatDayMonth } from '@/lib/time'

/** Value, gain, the day's move and XIRR of every fund I hold (or one bucket holds), next to
 * the same money in the benchmark and, for a bucket, in its model; and the SIPs. */
export function PortfolioSummary({ data }: { data: Portfolio }) {
  const total = data.returns
  const benchmark = data.benchmark
  const benchmarkName = data.benchmark_fund?.name ?? 'the benchmark'
  const day = data.day
  const sips = data.sips
  return (
    <div className="flex flex-col gap-2">
      <StatGrid className="lg:grid-cols-3">
        <Stat
          label="Value"
          value={total ? inr(total.value) : '—'}
          hint={`${inr(data.cost)} invested`}
          info={
            <InfoTip label="Value">
              Units held at each fund&apos;s latest NAV{total ? ` (${formatDate(total.on)})` : ''}.
            </InfoTip>
          }
        />
        <Stat
          label="Gain"
          value={total ? inr(total.gain) : '—'}
          tone={toneOf(total?.gain)}
          hint={total && `${formatPercent(total.return_pct)} · ${inr(data.realised)} realised`}
          info={
            <InfoTip label="Gain">
              Realised on what you sold plus unrealised on what you still hold.
            </InfoTip>
          }
        />
        <Stat
          label="Day"
          value={day ? inr(day.gain) : '—'}
          tone={toneOf(day?.gain)}
          hint={day && formatPercent(day.return_pct)}
          info={
            <InfoTip label="Day">
              Each fund&apos;s change between its last two NAVs, less money put in.
            </InfoTip>
          }
        />
        <Stat
          label="XIRR"
          value={formatPercent(total?.xirr_pct)}
          tone={toneOf(total?.xirr_pct)}
          hint={benchmark?.xirr_pct && `Benchmark: ${formatPercent(benchmark.xirr_pct)}`}
          info={
            <InfoTip label="XIRR">
              Yearly return on your dated purchases and sales, shown once you have held a year.
            </InfoTip>
          }
        />
        <Stat
          label="vs benchmark"
          value={data.ahead === null ? '—' : inr(data.ahead)}
          tone={toneOf(data.ahead)}
          hint={benchmark && `Same money: ${inr(benchmark.value)}`}
          info={
            <InfoTip label="vs benchmark">
              Your gain minus what the same purchases and sales, on the same dates, would have made
              in {benchmarkName}.
            </InfoTip>
          }
        />
        {data.model && (
          <Stat
            label="vs model"
            value={data.ahead_of_model === null ? '—' : inr(data.ahead_of_model)}
            tone={toneOf(data.ahead_of_model)}
            hint={data.model_returns && `Same money: ${inr(data.model_returns.value)}`}
            info={
              <InfoTip label="vs model">
                Your gain minus what the same purchases and sales, split by the model&apos;s weights
                on the same dates, would have made.
              </InfoTip>
            }
          />
        )}
        {(!data.bucket || sips.count > 0) && (
          <Stat
            label="SIPs a month"
            value={sips.count > 0 ? inr(sips.monthly) : '—'}
            hint={
              sips.next_date && sips.next_fund
                ? `Next ${formatDayMonth(sips.next_date)} · ${sips.next_fund.name}`
                : undefined
            }
          />
        )}
      </StatGrid>
      {data.missing_nav.length > 0 && (
        <p className="text-sm text-amber-700 dark:text-amber-400">
          No NAVs yet for {data.missing_nav.map((fund) => fund.name).join(', ')}.
        </p>
      )}
    </div>
  )
}

/** Fund values split by each fund's asset class. */
export function Allocation({ data }: { data: Portfolio }) {
  if (data.allocation.length === 0) return null
  return (
    <Section title="Allocation">
      <ul className="flex flex-col gap-3 text-sm">
        {data.allocation.map((slice) => (
          <li key={slice.asset} className="flex flex-col gap-1">
            <div className="flex justify-between gap-2">
              <span className="font-medium">{ASSET_LABELS[slice.asset]}</span>
              <span className="tabular-nums">
                {inr(slice.value)} · {formatPercent(slice.share, { sign: false })}
              </span>
            </div>
            {/* The width only draws the bar; the figure beside it comes from the API. */}
            <div className="bg-muted h-2 overflow-hidden rounded-full" aria-hidden>
              <div className="bg-primary h-full" style={{ width: `${slice.share ?? 0}%` }} />
            </div>
          </li>
        ))}
      </ul>
    </Section>
  )
}
