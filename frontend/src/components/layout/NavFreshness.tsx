import { Loader2, RefreshCw } from 'lucide-react'
import { toast } from 'sonner'

import { useHealth, useNavStatus, useSyncNavs } from '@/api/queries'
import { Button } from '@/components/ui/button'
import { syncMessage } from '@/lib/navs'
import { formatDate, formatDayMonth, previousWeekday, todayIst } from '@/lib/time'
import { cn } from '@/lib/utils'

type Tone = 'ok' | 'stale' | 'error'

/** How fresh the NAVs are, in the header; a click syncs them. Replaces the backend
 * badge: red also means the backend or its database is down. */
export function NavFreshness() {
  const health = useHealth()
  const status = useNavStatus()
  const sync = useSyncNavs()

  const down = health.isError || (health.isSuccess && health.data.database !== 'ok')
  if (down) {
    return (
      <Button
        variant="ghost"
        size="sm"
        className="text-destructive"
        aria-label="Backend unreachable. Check again"
        onClick={() => health.refetch()}
      >
        <Dot tone="error" />
        Offline
      </Button>
    )
  }

  const funds = status.data?.funds ?? []
  if (funds.length === 0) return null
  // ISO dates compare as strings: the newest NAV any tracked fund has.
  const latest = funds.reduce<string | null>(
    (max, row) =>
      row.coverage.last && (!max || row.coverage.last > max) ? row.coverage.last : max,
    null,
  )
  const failed = status.data?.last_run?.status === 'failed'
  const tone: Tone = failed
    ? 'error'
    : latest && latest >= previousWeekday(todayIst())
      ? 'ok'
      : 'stale'
  const label = latest ? `NAVs ${formatDayMonth(latest)}` : 'No NAVs'

  return (
    <Button
      variant="ghost"
      size="sm"
      disabled={sync.isPending}
      aria-label={`${latest ? `NAVs as of ${formatDate(latest)}` : 'No NAVs yet'}. Sync now`}
      title="Sync NAVs"
      onClick={() =>
        sync.mutate(undefined, {
          onSuccess: (run) =>
            run.failed > 0
              ? toast.error(`${run.failed} fund${run.failed === 1 ? '' : 's'} failed to sync`, {
                  description: 'Settings · Data has the details.',
                })
              : toast.success(syncMessage(run)),
          onError: (error) => toast.error(error.message),
        })
      }
    >
      <Dot tone={tone} />
      <span className={cn(tone === 'ok' && 'text-muted-foreground')}>{label}</span>
      {sync.isPending ? <Loader2 className="animate-spin" /> : <RefreshCw />}
    </Button>
  )
}

function Dot({ tone }: { tone: Tone }) {
  return (
    <span
      aria-hidden
      className={cn(
        'size-2 rounded-full',
        tone === 'ok' && 'bg-positive',
        tone === 'stale' && 'bg-amber-500',
        tone === 'error' && 'bg-destructive',
      )}
    />
  )
}
