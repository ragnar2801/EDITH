import { Settings2, Target, Wallet } from 'lucide-react'
import { Link, useSearchParams } from 'react-router'

import { useBuckets, useCash, type Bucket } from '@/api/queries'
import { EditBucketButton, NewBucketButton } from '@/components/buckets/Buckets'
import { CashPlan } from '@/components/cash/CashPlan'
import { EmptyState } from '@/components/EmptyState'
import { ErrorText } from '@/components/Field'
import { Loading } from '@/components/Loading'
import { PageHeader } from '@/components/PageHeader'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { NativeSelect } from '@/components/ui/native-select'
import { bucketLabel, bucketParam } from '@/lib/buckets'
import { modelPath } from '@/lib/models'

/** The bucket asked for in the address, else the first real one with a model. */
function chosen(buckets: Bucket[], asked: number | undefined): Bucket | undefined {
  return (
    buckets.find((b) => b.id === asked) ??
    buckets.find((b) => b.model && !b.paper) ??
    buckets.find((b) => b.model) ??
    buckets[0]
  )
}

/** I have ₹X: what do I buy for this bucket? One job (J5). */
export function InvestPage() {
  const cash = useCash()
  const buckets = useBuckets()
  const [params, setParams] = useSearchParams()
  const bucket = buckets.data && chosen(buckets.data, bucketParam(params.get('bucket')))
  const pick = (id: number) => setParams({ bucket: String(id) })

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Invest"
        meta={
          bucket &&
          buckets.data && (
            <span className="flex flex-wrap items-center gap-2">
              <label htmlFor="invest-bucket" className="sr-only">
                Bucket
              </label>
              <NativeSelect
                id="invest-bucket"
                className="h-8 w-auto min-w-40"
                value={bucket.id}
                onChange={(event) => pick(Number(event.target.value))}
              >
                {buckets.data.map((b) => (
                  <option key={b.id} value={b.id}>
                    {bucketLabel(b)}
                  </option>
                ))}
              </NativeSelect>
              {bucket.model && (
                <Badge asChild variant="outline">
                  <Link to={modelPath(bucket.model.id)}>{bucket.model.name}</Link>
                </Badge>
              )}
            </span>
          )
        }
        actions={
          <Button asChild variant="outline" size="sm">
            <Link to="/settings">
              <Settings2 /> Rules
            </Link>
          </Button>
        }
      />
      <ErrorText error={cash.error ?? buckets.error} />
      {(cash.isPending || buckets.isPending) && <Loading />}
      {cash.isSuccess && buckets.isSuccess && !bucket && (
        <EmptyState
          icon={Wallet}
          title="Make a bucket to invest into"
          action={<NewBucketButton onMade={(made) => pick(made.id)} />}
        />
      )}
      {cash.isSuccess && bucket && !bucket.model && (
        <EmptyState
          icon={Target}
          title={`Choose a model for ${bucket.name}`}
          action={<EditBucketButton bucket={bucket}>Choose a model</EditBucketButton>}
        />
      )}
      {cash.isSuccess && bucket?.model && (
        <CashPlan key={bucket.id} bucket={bucket} investable={cash.data.deployable} />
      )}
    </div>
  )
}
