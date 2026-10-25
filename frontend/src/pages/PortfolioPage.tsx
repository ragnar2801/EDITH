import { Link } from 'react-router'

import { useBuckets, useCash, useHoldings, usePlanSettings } from '@/api/queries'
import { CashAccounts } from '@/components/cash/CashAccounts'
import { CashSummary } from '@/components/cash/CashSummary'
import { ErrorText } from '@/components/Field'
import { Loading } from '@/components/Loading'
import { PageHeader } from '@/components/PageHeader'
import { FundListBanner } from '@/components/portfolio/FundListBanner'
import { HoldingsTable } from '@/components/portfolio/HoldingsTable'
import { SetupChecklist } from '@/components/portfolio/SetupChecklist'
import { RouteTabs } from '@/components/RouteTabs'
import { Button } from '@/components/ui/button'
import { useAddTransaction } from '@/hooks/use-add-transaction'
import { MODELS_PATH } from '@/lib/models'

/** What I own: funds and cash (D-063, D-064). */
export function PortfolioPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Portfolio" />
      <FundListBanner />
      <Setup />
      <RouteTabs
        label="Portfolio"
        tabs={[
          { path: '/', label: 'Funds', content: <HoldingsTable /> },
          { path: '/cash', label: 'Cash', content: <CashTab /> },
        ]}
      />
    </div>
  )
}

function Setup() {
  const cash = useCash()
  const holdings = useHoldings()
  const settings = usePlanSettings()
  const buckets = useBuckets()
  const addTransaction = useAddTransaction()
  if (!cash.isSuccess || !holdings.isSuccess || !settings.isSuccess || !buckets.isSuccess) {
    return null
  }

  return (
    <SetupChecklist
      steps={[
        {
          label: 'Add your cash',
          done: cash.data.accounts.length > 0,
          action: (
            <Button asChild size="sm" variant="outline">
              <Link to="/cash">Add cash</Link>
            </Button>
          ),
        },
        {
          label: 'Add your funds',
          done: holdings.data.length > 0,
          action: (
            <Button size="sm" variant="outline" onClick={() => addTransaction()}>
              Add transaction
            </Button>
          ),
        },
        {
          label: 'Choose a target model',
          done: settings.data.target_bucket !== null,
          action: (
            <Button asChild size="sm" variant="outline">
              <Link to={buckets.data.length > 0 ? MODELS_PATH : `${MODELS_PATH}/new`}>
                {buckets.data.length > 0 ? 'Choose' : 'New model'}
              </Link>
            </Button>
          ),
        },
      ]}
    />
  )
}

function CashTab() {
  const cash = useCash()
  if (cash.isPending) return <Loading />
  if (cash.isError) return <ErrorText error={cash.error} />
  return (
    <>
      <CashSummary cash={cash.data} />
      <CashAccounts accounts={cash.data.accounts} />
    </>
  )
}
