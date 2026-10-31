import { Copy, FlaskConical, Pencil, PieChart, Plus, Target, Trash2 } from 'lucide-react'
import { Link, useNavigate } from 'react-router'

import { useModels, usePlanSettings } from '@/api/queries'
import { Table, TBody, Td, Th, THead, Tr } from '@/components/DataTable'
import { EmptyState } from '@/components/EmptyState'
import { ErrorText } from '@/components/Field'
import { Loading } from '@/components/Loading'
import { useModelActions } from '@/components/models/useModelActions'
import { PageHeader } from '@/components/PageHeader'
import { RowActions } from '@/components/RowActions'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { MODELS_PATH, REBALANCE_LABELS, backtestPath, modelPath } from '@/lib/models'

/** Models (models): target splits to backtest and to invest towards. */
export function ModelsPage() {
  const models = useModels()
  const settings = usePlanSettings()
  const actions = useModelActions()
  const navigate = useNavigate()
  const targetId = settings.data?.target_model?.id
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
            <Th />
          </THead>
          <TBody>
            {models.data.map((model) => (
              <Tr key={model.id} to={modelPath(model.id)}>
                <Td>
                  <span className="flex flex-wrap items-center gap-2">
                    <Link
                      to={modelPath(model.id)}
                      className="font-medium underline-offset-4 hover:underline"
                    >
                      {model.name}
                    </Link>
                    {model.id === targetId && <Badge>Target</Badge>}
                  </span>
                </Td>
                <Td numeric>{model.funds.length}</Td>
                <Td>{REBALANCE_LABELS[model.rebalance]}</Td>
                <Td className="text-muted-foreground">{model.benchmark?.fund.name ?? '—'}</Td>
                <Td className="w-0">
                  <RowActions
                    label={`Actions for ${model.name}`}
                    actions={[
                      {
                        label: 'Set as target',
                        icon: Target,
                        hidden: model.id === targetId,
                        onSelect: () => actions.makeTarget(model),
                      },
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
