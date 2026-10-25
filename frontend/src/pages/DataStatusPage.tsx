import { Loader2, RefreshCw } from 'lucide-react'
import { Link } from 'react-router'

import { useNavStatus, useSyncNavs } from '@/api/queries'
import type { Schemas } from '@/api/client'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { planLabel } from '@/lib/instruments'
import { formatDate, formatDateTime } from '@/lib/time'

type SyncRun = Schemas['SyncRunOut']
type FundResult = Schemas['FundResultOut']

const RESULT_LABELS: Record<FundResult['status'], string> = {
  ok: 'ok',
  fallback: 'latest only',
  failed: 'failed',
}

export function DataStatusPage() {
  const status = useNavStatus()
  const sync = useSyncNavs()

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Data status</h1>
        <p className="text-muted-foreground mt-1">
          The fund NAVs Friday keeps, and when they were last brought up to date.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>NAV sync</CardTitle>
          <CardDescription>
            Downloads every missing NAV up to today for each tracked fund (from mfapi.in, with AMFI
            as the fallback). Same as <code>just navs</code>. Safe to run any time.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <Button
              onClick={() => sync.mutate(undefined)}
              disabled={sync.isPending || !status.data?.funds.length}
            >
              {sync.isPending ? <Loader2 className="animate-spin" /> : <RefreshCw />}
              Sync all NAVs
            </Button>
            {status.data?.last_run && <RunLine run={status.data.last_run} />}
          </div>
          <div aria-live="polite">
            {sync.isError && (
              <p role="alert" className="text-destructive text-sm">
                Sync failed: {sync.error.message}
              </p>
            )}
            {sync.isSuccess && <Failures run={sync.data} />}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Tracked funds</CardTitle>
          <CardDescription>
            Funds you track yourself, and every fund and benchmark in a bucket.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {status.isPending && <p className="text-muted-foreground text-sm">Loading…</p>}
          {status.isError && <p className="text-destructive text-sm">{status.error.message}</p>}
          {status.isSuccess && status.data.funds.length === 0 && (
            <p className="text-muted-foreground text-sm">
              No funds tracked yet. Open a fund from{' '}
              <Link to="/instruments" className="underline underline-offset-4">
                Instruments
              </Link>{' '}
              and press <strong>Track NAVs</strong>, or add it to a bucket.
            </p>
          )}
          {status.isSuccess && status.data.funds.length > 0 && (
            <div className="-mx-6 overflow-x-auto px-6">
              <table className="w-full min-w-[40rem] text-sm">
                <thead className="text-muted-foreground text-left text-xs">
                  <tr className="border-b">
                    <th className="py-2 pr-3 font-medium">Fund</th>
                    <th className="py-2 pr-3 font-medium">Kept because</th>
                    <th className="py-2 pr-3 text-right font-medium">NAVs</th>
                    <th className="py-2 pr-3 font-medium">First</th>
                    <th className="py-2 pr-3 font-medium">Latest</th>
                    <th className="py-2 pr-3 font-medium">Last sync</th>
                    <th className="py-2 font-medium">
                      <span className="sr-only">Actions</span>
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {status.data.funds.map((row) => (
                    <tr key={row.fund.id}>
                      <td className="py-2 pr-3">
                        <Link
                          to={`/instruments/${row.fund.id}`}
                          className="font-medium underline-offset-4 hover:underline"
                        >
                          {row.fund.name}
                        </Link>
                        <div className="text-muted-foreground text-xs">
                          AMFI {row.fund.amfi_code}
                          {planLabel(row.fund) && ` · ${planLabel(row.fund)}`}
                        </div>
                      </td>
                      <td className="text-muted-foreground py-2 pr-3 text-xs">
                        {[row.tracked_by_me ? 'you' : null, ...row.used_by]
                          .filter(Boolean)
                          .join(', ')}
                      </td>
                      <td className="py-2 pr-3 text-right tabular-nums">
                        {row.coverage.count.toLocaleString('en-IN')}
                      </td>
                      <td className="py-2 pr-3 whitespace-nowrap">
                        {row.coverage.first ? formatDate(row.coverage.first) : '—'}
                      </td>
                      <td className="py-2 pr-3 whitespace-nowrap">
                        {row.coverage.last ? formatDate(row.coverage.last) : '—'}
                      </td>
                      <td className="py-2 pr-3">
                        {row.last_result ? (
                          <Badge
                            variant={
                              row.last_result.status === 'failed' ? 'destructive' : 'outline'
                            }
                            title={row.last_result.message ?? undefined}
                          >
                            {RESULT_LABELS[row.last_result.status]}
                          </Badge>
                        ) : (
                          <span className="text-muted-foreground">never</span>
                        )}
                      </td>
                      <td className="py-2 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={sync.isPending}
                          onClick={() => sync.mutate([row.fund.id])}
                          aria-label={`Sync ${row.fund.name}`}
                        >
                          Sync
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function RunLine({ run }: { run: SyncRun }) {
  return (
    <p className="text-muted-foreground text-sm">
      Last sync {formatDateTime(run.finished_at)} · {run.funds} fund{run.funds === 1 ? '' : 's'} ·{' '}
      {run.added.toLocaleString('en-IN')} NAVs added
      {run.corrected > 0 && ` · ${run.corrected} corrected`}
      {run.status !== 'ok' && (
        <Badge variant="destructive" className="ml-2">
          {run.status}
        </Badge>
      )}
    </p>
  )
}

function Failures({ run }: { run: SyncRun }) {
  const notes = run.results.filter((result) => result.status !== 'ok')
  if (notes.length === 0) {
    return (
      <p className="text-sm">
        Done: {run.added.toLocaleString('en-IN')} NAVs added for {run.funds} fund
        {run.funds === 1 ? '' : 's'}.
      </p>
    )
  }
  return (
    <ul className="flex flex-col gap-1 text-sm">
      {notes.map((result) => (
        <li key={result.instrument_id}>
          <span className="font-medium">{result.name}</span>: {RESULT_LABELS[result.status]}.{' '}
          <span className="text-muted-foreground">{result.message}</span>
        </li>
      ))}
    </ul>
  )
}
