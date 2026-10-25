import { FlaskConical, Pencil, PieChart, Plus, Trash2 } from 'lucide-react'
import { Link, useNavigate } from 'react-router'
import { toast } from 'sonner'

import { useBuckets, useDeleteBucket } from '@/api/queries'
import { EmptyState } from '@/components/EmptyState'
import { ErrorText } from '@/components/Field'
import { Loading } from '@/components/Loading'
import { PageHeader } from '@/components/PageHeader'
import { RowActions } from '@/components/RowActions'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useConfirm } from '@/hooks/use-confirm'
import { REBALANCE_LABELS, type Bucket } from '@/lib/buckets'
import { fundPath, planLabel } from '@/lib/instruments'
import { MODELS_PATH, backtestPath } from '@/lib/models'

/** Models (buckets, D-061): target splits to backtest and to invest towards. */
export function BucketsPage() {
  const buckets = useBuckets()
  const newModel = (
    <Button asChild>
      <Link to={`${MODELS_PATH}/new`}>
        <Plus /> New model
      </Link>
    </Button>
  )

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6">
      <PageHeader title="Models" actions={newModel} />
      <ErrorText error={buckets.error} />
      {buckets.isPending && <Loading />}
      {buckets.isSuccess && buckets.data.length === 0 && (
        <EmptyState icon={PieChart} title="No models yet" action={newModel} />
      )}
      <div className="grid gap-4 md:grid-cols-2">
        {buckets.data?.map((bucket) => (
          <ModelCard key={bucket.id} bucket={bucket} />
        ))}
      </div>
    </div>
  )
}

function ModelCard({ bucket }: { bucket: Bucket }) {
  const remove = useDeleteBucket()
  const confirm = useConfirm()
  const navigate = useNavigate()

  async function onDelete() {
    const yes = await confirm({
      title: `Delete ${bucket.name}?`,
      description: 'Its saved backtests are deleted too.',
    })
    if (yes) remove.mutate(bucket.id, { onSuccess: () => toast.success(`${bucket.name} deleted`) })
  }

  return (
    <Card className="gap-4">
      <CardHeader className="grid-cols-[1fr_auto]">
        <CardTitle className="flex flex-wrap items-center gap-2">
          {bucket.name}
          <Badge variant="outline">{REBALANCE_LABELS[bucket.rebalance]}</Badge>
        </CardTitle>
        <RowActions
          label={`Actions for ${bucket.name}`}
          actions={[
            {
              label: 'Edit',
              icon: Pencil,
              onSelect: () => navigate(`${MODELS_PATH}/${bucket.id}/edit`),
            },
            { label: 'Delete', icon: Trash2, destructive: true, onSelect: () => void onDelete() },
          ]}
        />
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <ul className="flex flex-col gap-1.5 text-sm">
          {bucket.funds.map((member) => (
            <li key={member.fund.id} className="flex items-center justify-between gap-3">
              <Link
                to={fundPath(member.fund.id)}
                className="min-w-0 truncate underline-offset-4 hover:underline"
              >
                {member.fund.name}
                {planLabel(member.fund) && (
                  <span className="text-muted-foreground"> · {planLabel(member.fund)}</span>
                )}
              </Link>
              <span className="tabular-nums">{member.weight}%</span>
            </li>
          ))}
        </ul>
        <p className="text-muted-foreground text-xs">
          {bucket.benchmark ? `vs ${bucket.benchmark.fund.name}` : 'No benchmark'}
        </p>
        <div>
          <Button asChild size="sm" variant="outline">
            <Link to={backtestPath(bucket.id)}>
              <FlaskConical /> Backtest
            </Link>
          </Button>
        </div>
        <ErrorText error={remove.error} />
      </CardContent>
    </Card>
  )
}
