import { Download, Loader2 } from 'lucide-react'
import { toast } from 'sonner'

import { useInstrumentSources, useRefreshInstruments } from '@/api/queries'
import { ErrorText } from '@/components/Field'
import { Button } from '@/components/ui/button'

/** Search finds nothing until the fund list is downloaded: say so once, with the fix. */
export function FundListBanner() {
  const sources = useInstrumentSources()
  const refresh = useRefreshInstruments()
  const amfi = sources.data?.find((source) => source.source === 'amfi')
  if (!amfi || amfi.last_success) return null

  return (
    <div
      role="status"
      className="flex flex-wrap items-center gap-3 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm"
    >
      <span className="font-medium">Fund list not downloaded</span>
      <Button
        size="sm"
        className="ml-auto"
        disabled={refresh.isPending}
        onClick={() =>
          refresh.mutate(['amfi'], {
            onSuccess: ([result]) =>
              result.status === 'ok'
                ? toast.success(`${result.rows.toLocaleString('en-IN')} funds downloaded`)
                : toast.error(result.message ?? 'Download failed'),
          })
        }
      >
        {refresh.isPending ? <Loader2 className="animate-spin" /> : <Download />}
        {refresh.isPending ? 'Downloading…' : 'Download'}
      </Button>
      <ErrorText error={refresh.error} />
    </div>
  )
}
