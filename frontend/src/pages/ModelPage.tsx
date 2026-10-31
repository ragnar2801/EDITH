import { Copy, Pencil, Trash2 } from 'lucide-react'
import { Link, useParams } from 'react-router'

import { useBuckets, useModels, type Bucket } from '@/api/queries'
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
import { bucketPath } from '@/lib/buckets'
import { fundPath } from '@/lib/instruments'
import { MODELS_PATH, REBALANCE_LABELS, modelPath, type Model } from '@/lib/models'
import { inr } from '@/lib/money'
import { toneClass } from '@/lib/percent'

/** One model: what's in it, and how it would have done (J6). */
export function ModelPage() {
  const id = Number(useParams().id)
  const models = useModels()
  const actions = useModelActions()
  const model = models.data?.find((b) => b.id === id)
  const back = { to: MODELS_PATH, label: 'Models' }

  if (models.isPending) return <Loading />
  if (models.isError) return <ErrorText error={models.error} />
  if (!model) return <PageHeader back={back} title="Model not found" />

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        back={back}
        title={model.name}
        meta={
          <>
            <span>{REBALANCE_LABELS[model.rebalance]}</span>
            {model.benchmark && <span>vs {model.benchmark.fund.name}</span>}
          </>
        }
        actions={
          <>
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
            content: <Overview model={model} />,
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

function Overview({ model }: { model: Model }) {
  const buckets = useBuckets()
  const following = (buckets.data ?? []).filter((bucket) => bucket.model?.id === model.id)
  return (
    <>
      {model.description && <p className="text-sm">{model.description}</p>}
      <Section title="Funds">
        <Table label="Funds">
          <THead>
            <Th>Fund</Th>
            <Th numeric>Weight</Th>
          </THead>
          <TBody>
            {model.funds.map((member) => (
              <Tr key={member.fund.id} to={fundPath(member.fund.id)}>
                <Td>
                  <FundName fund={member.fund} />
                </Td>
                <Td numeric>{member.weight}%</Td>
              </Tr>
            ))}
          </TBody>
        </Table>
      </Section>
      {following.length > 0 && <Following buckets={following} />}
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

/** The buckets following the model, each against the same money in the model. */
function Following({ buckets }: { buckets: Bucket[] }) {
  return (
    <Section title="Buckets">
      <Table label="Buckets">
        <THead>
          <Th>Bucket</Th>
          <Th numeric>Value</Th>
          <Th numeric>Gain</Th>
          <Th numeric>
            <span className="inline-flex items-center gap-1">
              vs model
              <InfoTip label="vs model">
                The bucket&apos;s gain minus the same purchases and sales split by this model&apos;s
                weights.
              </InfoTip>
            </span>
          </Th>
        </THead>
        <TBody>
          {buckets.map((bucket) => (
            <Tr key={bucket.id} to={bucketPath(bucket.id)}>
              <Td>
                <span className="flex items-center gap-2 font-medium">
                  {bucket.name}
                  {bucket.paper && <Badge variant="outline">Paper</Badge>}
                </span>
              </Td>
              <Td numeric>{bucket.value ? inr(bucket.value) : '—'}</Td>
              <Td numeric className={toneClass(bucket.gain)}>
                {bucket.gain ? inr(bucket.gain) : '—'}
              </Td>
              <Td numeric className={toneClass(bucket.ahead_of_model)}>
                {bucket.ahead_of_model ? inr(bucket.ahead_of_model) : '—'}
              </Td>
            </Tr>
          ))}
        </TBody>
      </Table>
    </Section>
  )
}
