import { Link } from 'react-router'

import { useBuckets, useNavStatus } from '@/api/queries'
import { Stat, StatGrid } from '@/components/Stat'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { REBALANCE_LABELS } from '@/lib/buckets'
import { formatDateTime } from '@/lib/time'

/** Overview until the portfolio view arrives (T1-17): buckets, tracked funds, last sync. */
export function DashboardPage() {
  const buckets = useBuckets()
  const status = useNavStatus()
  const lastRun = status.data?.last_run

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground mt-1">
          Your target splits and the funds Friday keeps NAVs for. Portfolio value, P&amp;L and drift
          arrive with your holdings (T1-15 to T1-17).
        </p>
      </div>
      <StatGrid>
        <Stat label="Buckets" value={buckets.data?.length ?? '—'} />
        <Stat label="Tracked funds" value={status.data?.funds.length ?? '—'} />
        <Stat
          label="Last NAV sync"
          value={lastRun ? formatDateTime(lastRun.finished_at) : 'never'}
          hint={lastRun ? `${lastRun.added.toLocaleString('en-IN')} NAVs added` : undefined}
        />
      </StatGrid>

      {buckets.isSuccess && buckets.data.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>Get started in three steps</CardTitle>
          </CardHeader>
          <CardContent>
            <ol className="flex list-decimal flex-col gap-2 pl-5 text-sm">
              <li>
                <strong>Find your funds</strong>: search by name or scheme code in{' '}
                <Link to="/instruments" className="underline underline-offset-4">
                  Instruments
                </Link>
                .
              </li>
              <li>
                <strong>Build a bucket</strong>: your funds with target weights, compared with the
                Nifty 50.{' '}
                <Link to="/buckets" className="underline underline-offset-4">
                  Open Buckets
                </Link>
              </li>
              <li>
                <strong>Backtest it</strong>: lump sum, SIP, SWP or your own timeline.{' '}
                <Link to="/backtest" className="underline underline-offset-4">
                  Open Backtest
                </Link>
              </li>
            </ol>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Your buckets</CardTitle>
            <CardDescription>
              <Link to="/buckets" className="underline underline-offset-4">
                Manage buckets
              </Link>
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="divide-y text-sm">
              {buckets.data?.map((bucket) => (
                <li key={bucket.id} className="flex flex-wrap items-center gap-x-4 gap-y-1 py-2">
                  <span className="font-medium">{bucket.name}</span>
                  <span className="text-muted-foreground">
                    {bucket.funds.length} fund{bucket.funds.length === 1 ? '' : 's'} ·{' '}
                    {REBALANCE_LABELS[bucket.rebalance]}
                    {bucket.benchmark && ` · vs ${bucket.benchmark.fund.name}`}
                  </span>
                  <Button asChild size="sm" variant="outline" className="ml-auto">
                    <Link to={`/backtest/${bucket.id}`}>Backtest</Link>
                  </Button>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
