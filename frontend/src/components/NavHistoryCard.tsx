import { Loader2, RefreshCw } from 'lucide-react'
import { useState } from 'react'

import { useNavSummary, useNavs, useSyncNavs, useTrackFund, useUntrackFund } from '@/api/queries'
import { LineChart } from '@/components/charts/LineChart'
import { Stat, StatGrid } from '@/components/Stat'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { formatNav } from '@/lib/money'
import { formatPercent, toneOf } from '@/lib/percent'
import { rangeStart, usefulRanges, type RangeKey } from '@/lib/ranges'
import { formatDate } from '@/lib/time'

const axisNav = (value: number) => `₹${value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`

/** A fund's NAV history (T1-12): track it, sync it, see its chart and headline figures. */
export function NavHistoryCard({ instrumentId }: { instrumentId: number }) {
  const summary = useNavSummary(instrumentId)
  const track = useTrackFund(instrumentId)
  const untrack = useUntrackFund(instrumentId)
  const sync = useSyncNavs()
  const [range, setRange] = useState<RangeKey>('1Y')

  const data = summary.data
  const last = data?.coverage.last ?? null
  const first = data?.coverage.first ?? null
  const start = last ? (rangeStart(range, last) ?? undefined) : undefined
  const navs = useNavs(instrumentId, start, !!last)

  if (!data || !data.is_fund) return null
  const busy = track.isPending || sync.isPending || untrack.isPending
  const error = track.error ?? sync.error ?? untrack.error
  const stats = data.stats

  return (
    <Card>
      <CardHeader>
        <CardTitle>NAV history</CardTitle>
        <CardDescription>
          {data.tracked
            ? `Kept up to date${data.used_by.length ? ` (used by ${data.used_by.join(', ')})` : ''}. ${
                first && last
                  ? `${data.coverage.count.toLocaleString('en-IN')} NAVs from ${formatDate(first)} to ${formatDate(last)}.`
                  : 'No NAVs downloaded yet.'
              }`
            : 'Not tracked. Track it to download every NAV since launch and keep it up to date.'}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-wrap gap-2">
          {!data.tracked && (
            <Button onClick={() => track.mutate()} disabled={busy}>
              {track.isPending && <Loader2 className="animate-spin" />}
              Track NAVs
            </Button>
          )}
          {data.tracked && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => sync.mutate([instrumentId])}
              disabled={busy}
            >
              {sync.isPending ? <Loader2 className="animate-spin" /> : <RefreshCw />}
              Sync now
            </Button>
          )}
          {data.tracked_by_me && data.used_by.length === 0 && (
            <Button variant="ghost" size="sm" onClick={() => untrack.mutate()} disabled={busy}>
              Stop tracking
            </Button>
          )}
        </div>
        {error && (
          <p role="alert" className="text-destructive text-sm">
            {error.message}
          </p>
        )}
        {stats && (
          <StatGrid>
            <Stat
              label="Latest NAV"
              value={formatNav(stats.latest.nav)}
              hint={formatDate(stats.latest.date)}
            />
            <Stat
              label="1 day"
              value={formatPercent(stats.change_1d_pct)}
              tone={toneOf(stats.change_1d_pct)}
            />
            <Stat
              label="1 year"
              value={formatPercent(stats.change_1y_pct)}
              tone={toneOf(stats.change_1y_pct)}
            />
            <Stat
              label={`Since ${stats.first.date.slice(0, 4)}`}
              value={formatPercent(stats.change_since_first_pct)}
              tone={toneOf(stats.change_since_first_pct)}
            />
            <Stat
              label="CAGR since launch"
              value={formatPercent(stats.cagr_pct, { sign: false })}
            />
            <Stat
              label="52-week high"
              value={formatNav(stats.high_52w.nav)}
              hint={formatDate(stats.high_52w.date)}
            />
            <Stat
              label="52-week low"
              value={formatNav(stats.low_52w.nav)}
              hint={formatDate(stats.low_52w.date)}
            />
          </StatGrid>
        )}
        {first && last && (
          <div className="flex flex-col gap-2">
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
            <LineChart
              label="NAV over time"
              area
              height={260}
              series={[
                {
                  name: 'NAV',
                  color: 'var(--chart-main)',
                  points: (navs.data ?? []).map((point) => ({
                    date: point.date,
                    value: point.nav,
                  })),
                },
              ]}
              formatValue={formatNav}
              formatAxis={axisNav}
            />
          </div>
        )}
        {navs.data && navs.data.length > 0 && (
          <details className="text-sm">
            <summary className="text-muted-foreground cursor-pointer">Recent NAVs</summary>
            <table className="mt-2 w-full max-w-sm">
              <tbody className="divide-y">
                {navs.data
                  .slice(-10)
                  .reverse()
                  .map((point) => (
                    <tr key={point.date}>
                      <td className="py-1">{formatDate(point.date)}</td>
                      <td className="py-1 text-right tabular-nums">{formatNav(point.nav)}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </details>
        )}
      </CardContent>
    </Card>
  )
}
