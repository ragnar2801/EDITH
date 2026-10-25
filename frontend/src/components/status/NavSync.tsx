import { Loader2, RefreshCw } from 'lucide-react'
import { toast } from 'sonner'

import { useNavStatus, useSyncNavs } from '@/api/queries'
import { ErrorText } from '@/components/Field'
import { InfoTip } from '@/components/InfoTip'
import { Section } from '@/components/Section'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { RESULT_LABELS, syncMessage, type SyncRun } from '@/lib/navs'
import { formatDateTime } from '@/lib/time'

/** The last NAV sync and a button for the next one. */
export function NavSync() {
  const status = useNavStatus()
  const sync = useSyncNavs()
  const run = sync.data ?? status.data?.last_run

  return (
    <Section
      title="NAV sync"
      info={
        <InfoTip label="NAV sync">
          Downloads every missing NAV up to today for each tracked fund.
        </InfoTip>
      }
      actions={
        <Button
          size="sm"
          onClick={() =>
            sync.mutate(undefined, {
              onSuccess: (result) =>
                result.failed > 0
                  ? toast.error(`${result.failed} fund${result.failed === 1 ? '' : 's'} failed`)
                  : toast.success(syncMessage(result)),
            })
          }
          disabled={sync.isPending || !status.data?.funds.length}
        >
          {sync.isPending ? <Loader2 className="animate-spin" /> : <RefreshCw />}
          Sync all NAVs
        </Button>
      }
    >
      {run ? (
        <p className="text-muted-foreground flex flex-wrap items-center gap-2 text-sm">
          Last sync {formatDateTime(run.finished_at)} · {syncMessage(run)}
          {run.corrected > 0 && ` · ${run.corrected} corrected`}
          {run.status !== 'ok' && <Badge variant="destructive">{run.status}</Badge>}
        </p>
      ) : (
        <p className="text-muted-foreground text-sm">Never synced</p>
      )}
      <ErrorText error={sync.error} />
      {run && <Failures run={run} />}
    </Section>
  )
}

function Failures({ run }: { run: SyncRun }) {
  const notes = run.results.filter((result) => result.status !== 'ok')
  if (notes.length === 0) return null
  return (
    <ul aria-live="polite" className="flex flex-col gap-1 text-sm">
      {notes.map((result) => (
        <li key={result.instrument_id}>
          <span className="font-medium">{result.name}</span>: {RESULT_LABELS[result.status]}.{' '}
          <span className="text-muted-foreground">{result.message}</span>
        </li>
      ))}
    </ul>
  )
}
