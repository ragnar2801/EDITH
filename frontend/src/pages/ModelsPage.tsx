import { Copy, FlaskConical, Pencil, PieChart, Plus, Target, Trash2 } from 'lucide-react'
import { Link, useNavigate } from 'react-router'

import { useBuckets, usePlanSettings } from '@/api/queries'
import { Table, TBody, Td, Th, THead, Tr } from '@/components/DataTable'
import { EmptyState } from '@/components/EmptyState'
import { ErrorText } from '@/components/Field'
import { Loading } from '@/components/Loading'
import { useModelActions } from '@/components/models/useModelActions'
import { PageHeader } from '@/components/PageHeader'
import { RowActions } from '@/components/RowActions'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { REBALANCE_LABELS } from '@/lib/buckets'
import { MODELS_PATH, backtestPath, modelPath } from '@/lib/models'

/** Models (buckets, D-061): target splits to backtest and to invest towards. */
export function ModelsPage() {
  const buckets = useBuckets()
  const settings = usePlanSettings()
  const actions = useModelActions()
  const navigate = useNavigate()
  const targetId = settings.data?.target_bucket?.id
  const newModel = (
    <Button asChild>
      <Link to={`${MODELS_PATH}/new`}>
        <Plus /> New model
      </Link>
    </Button>
  )

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Models" actions={newModel} />
      <ErrorText error={buckets.error ?? actions.error} />
      {buckets.isPending && <Loading />}
      {buckets.isSuccess && buckets.data.length === 0 && (
        <EmptyState icon={PieChart} title="No models yet" action={newModel} />
      )}
      {buckets.isSuccess && buckets.data.length > 0 && (
        <Table label="Models">
          <THead>
            <Th>Model</Th>
            <Th numeric>Funds</Th>
            <Th>Rebalance</Th>
            <Th>Benchmark</Th>
            <Th />
          </THead>
          <TBody>
            {buckets.data.map((bucket) => (
              <Tr key={bucket.id} to={modelPath(bucket.id)}>
                <Td>
                  <span className="flex flex-wrap items-center gap-2">
                    <Link
                      to={modelPath(bucket.id)}
                      className="font-medium underline-offset-4 hover:underline"
                    >
                      {bucket.name}
                    </Link>
                    {bucket.id === targetId && <Badge>Target</Badge>}
                  </span>
                </Td>
                <Td numeric>{bucket.funds.length}</Td>
                <Td>{REBALANCE_LABELS[bucket.rebalance]}</Td>
                <Td className="text-muted-foreground">{bucket.benchmark?.fund.name ?? '—'}</Td>
                <Td className="w-0">
                  <RowActions
                    label={`Actions for ${bucket.name}`}
                    actions={[
                      {
                        label: 'Set as target',
                        icon: Target,
                        hidden: bucket.id === targetId,
                        onSelect: () => actions.makeTarget(bucket),
                      },
                      {
                        label: 'Backtest',
                        icon: FlaskConical,
                        onSelect: () => navigate(backtestPath(bucket.id)),
                      },
                      {
                        label: 'Edit',
                        icon: Pencil,
                        onSelect: () => navigate(modelPath(bucket.id, 'edit')),
                      },
                      {
                        label: 'Duplicate',
                        icon: Copy,
                        onSelect: () => actions.duplicate(bucket),
                      },
                      {
                        label: 'Delete',
                        icon: Trash2,
                        destructive: true,
                        onSelect: () => void actions.remove(bucket),
                      },
                    ]}
                  />
                </Td>
              </Tr>
            ))}
          </TBody>
        </Table>
      )}
    </div>
  )
}
