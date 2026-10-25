import { PieChart } from 'lucide-react'
import { Link } from 'react-router'

import { useBuckets, useNavStatus } from '@/api/queries'
import { EmptyState } from '@/components/EmptyState'
import { PageHeader } from '@/components/PageHeader'
import { Section } from '@/components/Section'
import { Stat, StatGrid } from '@/components/Stat'
import { Button } from '@/components/ui/button'
import { REBALANCE_LABELS } from '@/lib/buckets'
import { MODELS_PATH, backtestPath } from '@/lib/models'
import { formatDateTime } from '@/lib/time'

export function DashboardPage() {
  const buckets = useBuckets()
  const status = useNavStatus()
  const lastRun = status.data?.last_run

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-8">
      <PageHeader title="Dashboard" />
      <StatGrid>
        <Stat label="Models" value={buckets.data?.length ?? '—'} />
        <Stat label="Tracked funds" value={status.data?.funds.length ?? '—'} />
        <Stat
          label="Last NAV sync"
          value={lastRun ? formatDateTime(lastRun.finished_at) : 'Never'}
          hint={lastRun ? `${lastRun.added.toLocaleString('en-IN')} NAVs added` : undefined}
        />
      </StatGrid>

      {buckets.isSuccess && buckets.data.length === 0 ? (
        <EmptyState
          icon={PieChart}
          title="No models yet"
          action={
            <Button asChild>
              <Link to={`${MODELS_PATH}/new`}>New model</Link>
            </Button>
          }
        />
      ) : (
        <Section title="Models">
          <ul className="divide-y rounded-lg border text-sm">
            {buckets.data?.map((bucket) => (
              <li key={bucket.id} className="flex flex-wrap items-center gap-x-4 gap-y-1 px-3 py-2">
                <span className="font-medium">{bucket.name}</span>
                <span className="text-muted-foreground">
                  {bucket.funds.length} fund{bucket.funds.length === 1 ? '' : 's'} ·{' '}
                  {REBALANCE_LABELS[bucket.rebalance]}
                  {bucket.benchmark && ` · vs ${bucket.benchmark.fund.name}`}
                </span>
                <Button asChild size="sm" variant="outline" className="ml-auto">
                  <Link to={backtestPath(bucket.id)}>Backtest</Link>
                </Button>
              </li>
            ))}
          </ul>
        </Section>
      )}
    </div>
  )
}
