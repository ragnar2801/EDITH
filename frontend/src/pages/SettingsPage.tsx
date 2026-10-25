import { Download, Loader2 } from 'lucide-react'
import { toast } from 'sonner'

import { usePlanSettings, useRefreshInstruments } from '@/api/queries'
import { InvestRulesForm } from '@/components/cash/InvestRules'
import { FundLists } from '@/components/data/FundLists'
import { NavSync } from '@/components/data/NavSync'
import { TrackedFunds } from '@/components/data/TrackedFunds'
import { ErrorText } from '@/components/Field'
import { Loading } from '@/components/Loading'
import { PageHeader } from '@/components/PageHeader'
import { RouteTabs } from '@/components/RouteTabs'
import { Button } from '@/components/ui/button'

/** Set once, rarely touched: the invest rules and the data behind everything. */
export function SettingsPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Settings" />
      <RouteTabs
        label="Settings"
        tabs={[
          { path: '/settings', label: 'Invest rules', content: <Rules /> },
          { path: '/settings/data', label: 'Data', content: <Data /> },
        ]}
      />
    </div>
  )
}

function Rules() {
  const settings = usePlanSettings()
  if (settings.isPending) return <Loading />
  if (settings.isError) return <ErrorText error={settings.error} />
  return (
    <div className="max-w-3xl">
      <InvestRulesForm key={settings.data.updated_at} settings={settings.data} />
    </div>
  )
}

function Data() {
  const refresh = useRefreshInstruments()
  return (
    <>
      <NavSync />
      <TrackedFunds />
      <FundLists
        actions={
          <Button
            size="sm"
            variant="outline"
            disabled={refresh.isPending}
            onClick={() =>
              refresh.mutate(undefined, {
                onSuccess: (results) => {
                  const failed = results.filter((result) => result.status !== 'ok')
                  if (failed.length > 0) {
                    toast.error(
                      `${failed.map((result) => result.source.toUpperCase()).join(', ')} failed`,
                    )
                  } else toast.success('Lists downloaded')
                },
              })
            }
          >
            {refresh.isPending ? <Loader2 className="animate-spin" /> : <Download />}
            {refresh.isPending ? 'Downloading…' : 'Download lists'}
          </Button>
        }
      />
      <ErrorText error={refresh.error} />
    </>
  )
}
