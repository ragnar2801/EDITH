import { Copy, Loader2, RefreshCw } from 'lucide-react'
import { toast } from 'sonner'

import { useFmStatus, useImportFm } from '@/api/queries'
import type { Schemas } from '@/api/client'
import { ErrorText } from '@/components/Field'
import { InfoTip } from '@/components/InfoTip'
import { Section } from '@/components/Section'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { formatDateTime } from '@/lib/time'

type FmImport = Schemas['FmImportOut']

function counts(run: FmImport): string {
  return `${run.lots} purchases and ${run.sales} sales of ${run.funds} funds`
}

/** Where FM's Sync to PC on the phone points, and what its last push brought in. */
export function PhoneSync() {
  const status = useFmStatus()
  const again = useImportFm()
  const run = again.data ?? status.data?.last_import

  return (
    <Section
      title="Phone sync"
      info={
        <InfoTip label="Phone sync">
          Purchases and sales from FM on your phone, sent with its Sync to PC.
        </InfoTip>
      }
      actions={
        <Button
          size="sm"
          variant="outline"
          disabled={again.isPending || !status.data?.has_copy}
          onClick={() =>
            again.mutate(undefined, { onSuccess: (result) => toast.success(counts(result)) })
          }
        >
          {again.isPending ? <Loader2 className="animate-spin" /> : <RefreshCw />}
          Import again
        </Button>
      }
    >
      <ErrorText error={status.error ?? again.error} />
      {status.isSuccess && (
        <ul className="divide-y rounded-lg border text-sm">
          <li className="flex flex-wrap justify-between gap-x-4 gap-y-1 px-3 py-2">
            <span className="font-medium">Address</span>
            <span className="text-muted-foreground tabular-nums">
              {status.data.receiver
                ? status.data.receiver.addresses.length
                  ? status.data.receiver.addresses.join(' or ')
                  : 'No network'
                : 'Off'}
            </span>
          </li>
          {status.data.receiver && (
            <>
              <li className="flex flex-wrap justify-between gap-x-4 gap-y-1 px-3 py-2">
                <span className="font-medium">Port</span>
                <span className="text-muted-foreground tabular-nums">
                  {status.data.receiver.port}
                </span>
              </li>
              <Token token={status.data.receiver.token} />
            </>
          )}
          <li className="flex flex-wrap justify-between gap-x-4 gap-y-1 px-3 py-2">
            <span className="font-medium">Last import</span>
            {run ? <LastImport run={run} /> : <span className="text-muted-foreground">Never</span>}
          </li>
        </ul>
      )}
      {run && run.warnings.length > 0 && (
        <ul className="text-muted-foreground list-disc space-y-1 pl-5 text-xs">
          {run.warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      )}
    </Section>
  )
}

function Token({ token }: { token: string }) {
  return (
    <li className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 px-3 py-2">
      <span className="font-medium">Token</span>
      <span className="flex items-center gap-1">
        <code className="text-muted-foreground text-xs break-all">{token}</code>
        <Button
          size="sm"
          variant="ghost"
          className="h-7"
          aria-label="Copy the token"
          onClick={() =>
            void navigator.clipboard.writeText(token).then(() => toast.success('Token copied'))
          }
        >
          <Copy />
        </Button>
      </span>
    </li>
  )
}

function LastImport({ run }: { run: FmImport }) {
  if (run.status === 'failed') {
    return (
      <span className="flex flex-wrap items-center gap-2">
        <Badge variant="destructive">Failed</Badge>
        <span className="text-destructive text-xs">
          {formatDateTime(run.imported_at)}: {run.message}
        </span>
      </span>
    )
  }
  return (
    <span className="text-muted-foreground">
      {formatDateTime(run.imported_at)} · {counts(run)}
    </span>
  )
}
