import { Link } from 'react-router'

import { useModels, useCash, useHoldings, usePlanSettings, usePortfolio } from '@/api/queries'
import { CashAccounts } from '@/components/cash/CashAccounts'
import { CashSummary } from '@/components/cash/CashSummary'
import { ErrorText } from '@/components/Field'
import { Loading } from '@/components/Loading'
import { PageHeader } from '@/components/PageHeader'
import { FundListBanner } from '@/components/portfolio/FundListBanner'
import { HoldingsTable } from '@/components/portfolio/HoldingsTable'
import { Allocation, PortfolioSummary } from '@/components/portfolio/PortfolioSummary'
import { SetupChecklist } from '@/components/portfolio/SetupChecklist'
import { TargetDrift } from '@/components/portfolio/TargetDrift'
import { ValueChart } from '@/components/portfolio/ValueChart'
import { RouteTabs } from '@/components/RouteTabs'
import { Button } from '@/components/ui/button'
import { useAddTransaction } from '@/hooks/use-add-transaction'
import { MODELS_PATH } from '@/lib/models'

/** What I own: funds and cash. */
export function PortfolioPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Portfolio" />
      <FundListBanner />
      <Setup />
      <RouteTabs
        label="Portfolio"
        tabs={[
          { path: '/', label: 'Funds', content: <FundsTab /> },
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
  const models = useModels()
  const addTransaction = useAddTransaction()
  if (!cash.isSuccess || !holdings.isSuccess || !settings.isSuccess || !models.isSuccess) {
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
          done: settings.data.target_model !== null,
          action: (
            <Button asChild size="sm" variant="outline">
              <Link to={models.data.length > 0 ? MODELS_PATH : `${MODELS_PATH}/new`}>
                {models.data.length > 0 ? 'Choose' : 'New model'}
              </Link>
            </Button>
          ),
        },
      ]}
    />
  )
}

/** Totals, the value chart, the target model and allocation appear once a fund is held; the
 * table shows its own empty state. */
function FundsTab() {
  const portfolio = usePortfolio()
  const held = portfolio.data?.funds.length ? portfolio.data : undefined
  return (
    <>
      <ErrorText error={portfolio.error} />
      {held && <PortfolioSummary data={held} />}
      {held && <ValueChart portfolio={held} />}
      <HoldingsTable portfolio={portfolio.data} />
      {held && (
        <div className="grid gap-6 lg:grid-cols-2">
          <TargetDrift data={held} />
          <Allocation data={held} />
        </div>
      )}
    </>
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
