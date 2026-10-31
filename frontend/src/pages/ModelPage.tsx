import { Copy, Pencil, Target, Trash2 } from 'lucide-react'
import { Link, useParams } from 'react-router'

import { useModels, usePlanSettings, usePortfolio } from '@/api/queries'
import { BacktestWorkspace } from '@/components/backtest/BacktestWorkspace'
import { OptimiseWorkspace } from '@/components/backtest/OptimiseWorkspace'
import { Table, TBody, Td, Th, THead, Tr } from '@/components/DataTable'
import { ErrorText } from '@/components/Field'
import { InfoTip } from '@/components/InfoTip'
import { Loading } from '@/components/Loading'
import { FundName } from '@/components/models/FundName'
import { useModelActions } from '@/components/models/useModelActions'
import { PageHeader } from '@/components/PageHeader'
import { RouteTabs } from '@/components/RouteTabs'
import { RowActions } from '@/components/RowActions'
import { Section } from '@/components/Section'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { MODELS_PATH, REBALANCE_LABELS, modelPath, type Model } from '@/lib/models'
import { fundPath } from '@/lib/instruments'
import { formatPercent, formatPoints } from '@/lib/percent'

/** One model: what's in it, and how it would have done (J6). */
export function ModelPage() {
  const id = Number(useParams().id)
  const models = useModels()
  const settings = usePlanSettings()
  const actions = useModelActions()
  const model = models.data?.find((b) => b.id === id)
  const back = { to: MODELS_PATH, label: 'Models' }

  if (models.isPending) return <Loading />
  if (models.isError) return <ErrorText error={models.error} />
  if (!model) return <PageHeader back={back} title="Model not found" />

  const isTarget = settings.data?.target_model?.id === model.id
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        back={back}
        title={model.name}
        meta={
          <>
            {isTarget && (
              <span className="flex items-center gap-1">
                <Badge>Target</Badge>
                <InfoTip label="Target">The model new cash moves you towards.</InfoTip>
              </span>
            )}
            <span>{REBALANCE_LABELS[model.rebalance]}</span>
            {model.benchmark && <span>vs {model.benchmark.fund.name}</span>}
          </>
        }
        actions={
          <>
            {!isTarget && settings.isSuccess && (
              <Button variant="outline" onClick={() => actions.makeTarget(model)}>
                <Target /> Set as target
              </Button>
            )}
            <Button asChild variant="outline">
              <Link to={modelPath(model.id, 'edit')}>
                <Pencil /> Edit
              </Link>
            </Button>
            <RowActions
              label={`More for ${model.name}`}
              actions={[
                {
                  label: 'Duplicate',
                  icon: Copy,
                  onSelect: () => actions.duplicate(model),
                },
                {
                  label: 'Delete',
                  icon: Trash2,
                  destructive: true,
                  onSelect: () => void actions.remove(model, MODELS_PATH),
                },
              ]}
            />
          </>
        }
      />
      <ErrorText error={actions.error} />
      <RouteTabs
        label="Model"
        tabs={[
          {
            path: modelPath(model.id),
            label: 'Overview',
            content: <Overview model={model} isTarget={isTarget} />,
          },
          {
            path: modelPath(model.id, 'backtest'),
            label: 'Backtest',
            content: <BacktestWorkspace model={model} />,
          },
          {
            path: modelPath(model.id, 'optimise'),
            label: 'Optimise',
            content: <OptimiseWorkspace model={model} />,
          },
        ]}
      />
    </div>
  )
}

function Overview({ model, isTarget }: { model: Model; isTarget: boolean }) {
  const portfolio = usePortfolio({ enabled: isTarget })
  // Drift is worked out for the target model only.
  const drift = isTarget ? new Map(portfolio.data?.drift.map((row) => [row.fund.id, row])) : null
  return (
    <>
      {model.description && <p className="text-sm">{model.description}</p>}
      <Section title="Funds">
        <Table label="Funds">
          <THead>
            <Th>Fund</Th>
            <Th numeric>Weight</Th>
            {drift && (
              <>
                <Th numeric>Now</Th>
                <Th numeric>
                  <span className="inline-flex items-center gap-1">
                    Drift
                    <InfoTip label="Drift">
                      Now minus weight, in percentage points; new cash in Invest closes it without
                      selling.
                    </InfoTip>
                  </span>
                </Th>
              </>
            )}
          </THead>
          <TBody>
            {model.funds.map((member) => (
              <Tr key={member.fund.id} to={fundPath(member.fund.id)}>
                <Td>
                  <FundName fund={member.fund} />
                </Td>
                <Td numeric>{member.weight}%</Td>
                {drift && (
                  <>
                    <Td numeric>
                      {formatPercent(drift.get(member.fund.id)?.share, { sign: false })}
                    </Td>
                    <Td numeric>{formatPoints(drift.get(member.fund.id)?.drift)}</Td>
                  </>
                )}
              </Tr>
            ))}
          </TBody>
        </Table>
      </Section>
      {model.benchmark && (
        <Section
          title="Benchmark"
          info={
            <InfoTip label="Benchmark">
              Backtests compare the model with the same money in this fund.
            </InfoTip>
          }
        >
          <Link to={fundPath(model.benchmark.fund.id)} className="w-fit hover:underline">
            <FundName fund={model.benchmark.fund} />
          </Link>
        </Section>
      )}
    </>
  )
}
