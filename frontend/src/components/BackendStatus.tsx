import { RefreshCw } from 'lucide-react'

import { useHealth } from '@/api/queries'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export function BackendStatus() {
  const health = useHealth()

  if (health.isPending) {
    return <Badge variant="outline">backend: checking…</Badge>
  }

  const ok = health.isSuccess && health.data.database === 'ok'
  const label = health.isSuccess
    ? `backend: ${ok ? 'ok' : 'database error'}`
    : 'backend: unreachable'

  return (
    <div className="flex items-center gap-1">
      <Badge variant="outline" title={health.isSuccess ? `v${health.data.version}` : undefined}>
        <span
          aria-hidden
          className={cn('size-2 rounded-full', ok ? 'bg-positive' : 'bg-destructive')}
        />
        {label}
      </Badge>
      {!ok && (
        <Button
          variant="ghost"
          size="icon"
          className="size-6"
          aria-label="Check again"
          onClick={() => health.refetch()}
        >
          <RefreshCw />
        </Button>
      )}
    </div>
  )
}
