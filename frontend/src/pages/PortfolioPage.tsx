import { Banknote } from 'lucide-react'
import { Link, useSearchParams } from 'react-router'

import { useBuckets, useCash, usePortfolio, type Bucket } from '@/api/queries'
import { Buckets, EditBucketButton, NewBucketButton } from '@/components/buckets/Buckets'
import { CashAccounts } from '@/components/cash/CashAccounts'
import { CashSummary } from '@/components/cash/CashSummary'
import { ErrorText } from '@/components/Field'
import { InfoTip } from '@/components/InfoTip'
import { Loading } from '@/components/Loading'
import { PageHeader } from '@/components/PageHeader'
import { FundListBanner } from '@/components/portfolio/FundListBanner'
import { HoldingsTable } from '@/components/portfolio/HoldingsTable'
import { ModelDrift } from '@/components/portfolio/ModelDrift'
import { Allocation, PortfolioSummary } from '@/components/portfolio/PortfolioSummary'
import { ValueChart } from '@/components/portfolio/ValueChart'
import { RouteTabs } from '@/components/RouteTabs'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { NativeSelect } from '@/components/ui/native-select'
import { bucketLabel, bucketParam, investPath } from '@/lib/buckets'

/** What I own: funds, the buckets they're set aside in, and cash. */
export function PortfolioPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Portfolio" />
      <FundListBanner />
      <RouteTabs
        label="Portfolio"
        tabs={[
          { path: '/', label: 'Funds', content: <FundsTab /> },
          { path: '/buckets', label: 'Buckets', content: <Buckets /> },
          { path: '/cash', label: 'Cash', content: <CashTab /> },
        ]}
      />
    </div>
  )
}

/** Real money, or one bucket picked above the figures. Totals, the value chart, the model and
 * allocation appear once a fund is held; the table shows its own empty state. */
function FundsTab() {
  const [params, setParams] = useSearchParams()
  const buckets = useBuckets()
  const chosen = bucketParam(params.get('bucket'))
  const bucket = buckets.data?.find((b) => b.id === chosen)
  const portfolio = usePortfolio({ bucket: chosen })
  const held = portfolio.data?.funds.length ? portfolio.data : undefined

  function pick(id: string) {
    setParams(id ? { bucket: id } : {})
  }

  return (
    <>
      {buckets.data && buckets.data.length > 0 && (
        <BucketBar buckets={buckets.data} bucket={bucket} onPick={pick} />
      )}
      <ErrorText error={portfolio.error} />
      {held && <PortfolioSummary data={held} />}
      {held && <ValueChart portfolio={held} />}
      <HoldingsTable portfolio={portfolio.data} bucket={chosen} />
      {held && (
        <div className="grid gap-6 lg:grid-cols-2">
          <ModelDrift data={held} />
          <Allocation data={held} />
        </div>
      )}
    </>
  )
}

function BucketBar({
  buckets,
  bucket,
  onPick,
}: {
  buckets: Bucket[]
  bucket?: Bucket
  onPick: (id: string) => void
}) {
  const real = buckets.filter((b) => !b.paper)
  const paper = buckets.filter((b) => b.paper)
  return (
    <div className="flex flex-wrap items-center gap-2">
      <label htmlFor="bucket" className="sr-only">
        Bucket
      </label>
      <NativeSelect
        id="bucket"
        className="w-auto min-w-48"
        value={bucket ? String(bucket.id) : ''}
        onChange={(event) => onPick(event.target.value)}
      >
        <option value="">All buckets</option>
        {real.map((b) => (
          <option key={b.id} value={b.id}>
            {b.name}
          </option>
        ))}
        {paper.length > 0 && (
          <optgroup label="Paper">
            {paper.map((b) => (
              <option key={b.id} value={b.id}>
                {bucketLabel(b)}
              </option>
            ))}
          </optgroup>
        )}
      </NativeSelect>
      {!bucket && (
        <InfoTip label="All buckets">
          Every real purchase, in a bucket or not. Paper buckets show only on their own.
        </InfoTip>
      )}
      {bucket?.paper && <Badge variant="outline">Paper</Badge>}
      {bucket && !bucket.model && (
        <EditBucketButton bucket={bucket} size="sm" variant="outline">
          Choose a model
        </EditBucketButton>
      )}
      {bucket?.model && (
        <Button asChild size="sm" variant="outline" className="ml-auto">
          <Link to={investPath(bucket.id)}>
            <Banknote /> Invest
          </Link>
        </Button>
      )}
      {!bucket && <NewBucketButton size="sm" variant="ghost" className="ml-auto" />}
    </div>
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
