import { X } from 'lucide-react'

import { useCompareBacktests, type BacktestRun } from '@/api/queries'
import { ErrorText } from '@/components/Field'
import { InfoTip } from '@/components/InfoTip'
import { Stat, StatGrid, type Tone } from '@/components/Stat'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { STRATEGY_LABELS } from '@/lib/backtest'
import { inrShort } from '@/lib/money'
import { formatPercent, formatPoints, toneOf } from '@/lib/percent'

/** Lower is better for these, so a rise is shown in red. */
const flip = (tone: Tone | undefined): Tone | undefined =>
  tone === 'positive' ? 'negative' : tone === 'negative' ? 'positive' : undefined

/** "+₹1.2L" / "−₹40K" for a change in rupees from the API. */
function signedInr(amount: string): string {
  const tone = toneOf(amount)
  if (tone === 'negative') return `−${inrShort(amount.slice(1))}`
  return tone === 'positive' ? `+${inrShort(amount)}` : inrShort(amount)
}

const weight = (value: string | null) => (value === null ? '—' : `${value}%`)

/** What changed against an earlier run: every figure is the API's. */
export function RunComparison({
  run,
  baseline,
  onClear,
}: {
  run: BacktestRun
  baseline: BacktestRun
  onClear: () => void
}) {
  const compare = useCompareBacktests(run.id, baseline.id)
  const c = compare.data

  return (
    <Card>
      <CardContent className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline">
            vs {baseline.name ?? `previous run (${STRATEGY_LABELS[baseline.strategy]})`}
          </Badge>
          {c && !c.same_settings && (
            <span className="flex items-center gap-1">
              <Badge variant="secondary">Settings differ</Badge>
              <InfoTip label="Settings differ">
                More than the split changed between the two runs.
              </InfoTip>
            </span>
          )}
          <Button
            size="icon"
            variant="ghost"
            className="ml-auto size-7"
            aria-label="Stop comparing"
            onClick={onClear}
          >
            <X />
          </Button>
        </div>
        <ErrorText error={compare.error} />
        {c && (
          <>
            <StatGrid>
              <Stat label="Final value" value={signedInr(c.end_value)} tone={toneOf(c.end_value)} />
              <Stat label="XIRR" value={formatPoints(c.xirr_pct)} tone={toneOf(c.xirr_pct)} />
              <Stat label="CAGR" value={formatPoints(c.cagr_pct)} tone={toneOf(c.cagr_pct)} />
              <Stat
                label="Absolute return"
                value={formatPoints(c.absolute_return_pct)}
                tone={toneOf(c.absolute_return_pct)}
              />
              <Stat
                label="Max drawdown"
                value={formatPoints(c.max_drawdown_pct)}
                tone={flip(toneOf(c.max_drawdown_pct))}
              />
              <Stat
                label="Volatility"
                value={formatPoints(c.volatility_pct)}
                tone={flip(toneOf(c.volatility_pct))}
              />
              <Stat
                label="Sharpe"
                value={formatPercent(c.sharpe).replace('%', '')}
                tone={toneOf(c.sharpe)}
              />
            </StatGrid>
            {c.weights.length > 0 && (
              <ul aria-label="Weights changed" className="flex flex-col gap-1 text-sm">
                {c.weights.map((change) => (
                  <li key={change.instrument_id} className="flex gap-2">
                    <span className="min-w-0 truncate">{change.name}</span>
                    <span className="text-muted-foreground ml-auto shrink-0 tabular-nums">
                      {weight(change.before)} → {weight(change.after)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}
