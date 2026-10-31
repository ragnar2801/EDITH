import { Copy, FlaskConical, Pencil, PieChart, Plus, Trash2 } from 'lucide-react'
import { Link, useNavigate } from 'react-router'

import { useBuckets, useModels } from '@/api/queries'
import { Table, TBody, Td, Th, THead, Tr } from '@/components/DataTable'
import { EmptyState } from '@/components/EmptyState'
import { ErrorText } from '@/components/Field'
import { Loading } from '@/components/Loading'
import { useModelActions } from '@/components/models/useModelActions'
import { PageHeader } from '@/components/PageHeader'
import { RowActions } from '@/components/RowActions'
import { Button } from '@/components/ui/button'
import { bucketLabel } from '@/lib/buckets'
import { MODELS_PATH, REBALANCE_LABELS, backtestPath, modelPath } from '@/lib/models'

/** Models: splits of funds to backtest, and for buckets to invest towards. */
export function ModelsPage() {
  const models = useModels()
  const buckets = useBuckets()
  const actions = useModelActions()
  const navigate = useNavigate()
  const followers = (id: number) =>
    (buckets.data ?? []).filter((bucket) => bucket.model?.id === id).map(bucketLabel)
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
      <ErrorText error={models.error ?? actions.error} />
      {models.isPending && <Loading />}
      {models.isSuccess && models.data.length === 0 && (
        <EmptyState icon={PieChart} title="No models yet" action={newModel} />
      )}
      {models.isSuccess && models.data.length > 0 && (
        <Table label="Models">
          <THead>
            <Th>Model</Th>
            <Th numeric>Funds</Th>
            <Th>Rebalance</Th>
            <Th>Benchmark</Th>
            <Th>Buckets</Th>
            <Th />
          </THead>
          <TBody>
            {models.data.map((model) => (
              <Tr key={model.id} to={modelPath(model.id)}>
                <Td>
                  <Link
                    to={modelPath(model.id)}
                    className="font-medium underline-offset-4 hover:underline"
                  >
                    {model.name}
                  </Link>
                </Td>
                <Td numeric>{model.funds.length}</Td>
                <Td>{REBALANCE_LABELS[model.rebalance]}</Td>
                <Td className="text-muted-foreground">{model.benchmark?.fund.name ?? '—'}</Td>
                <Td className="text-muted-foreground">{followers(model.id).join(', ') || '—'}</Td>
                <Td className="w-0">
                  <RowActions
                    label={`Actions for ${model.name}`}
                    actions={[
                      {
                        label: 'Backtest',
                        icon: FlaskConical,
                        onSelect: () => navigate(backtestPath(model.id)),
                      },
                      {
                        label: 'Edit',
                        icon: Pencil,
                        onSelect: () => navigate(modelPath(model.id, 'edit')),
                      },
                      {
                        label: 'Duplicate',
                        icon: Copy,
                        onSelect: () => actions.duplicate(model),
                      },
                      {
                        label: 'Delete',
                        icon: Trash2,
                        destructive: true,
                        onSelect: () => void actions.remove(model),
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
