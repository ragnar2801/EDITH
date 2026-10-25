import { Pencil, Target, Trash2 } from 'lucide-react'
import { Link, useParams } from 'react-router'

import { useBuckets, usePlanSettings, usePortfolio } from '@/api/queries'
import { BacktestWorkspace } from '@/components/backtest/BacktestWorkspace'
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
import { REBALANCE_LABELS, type Bucket } from '@/lib/buckets'
import { fundPath } from '@/lib/instruments'
import { MODELS_PATH, modelPath } from '@/lib/models'
import { formatPercent } from '@/lib/percent'

/** One model: what's in it, and how it would have done (J6). */
export function ModelPage() {
  const id = Number(useParams().id)
  const buckets = useBuckets()
  const settings = usePlanSettings()
  const actions = useModelActions()
  const bucket = buckets.data?.find((b) => b.id === id)
  const back = { to: MODELS_PATH, label: 'Models' }

  if (buckets.isPending) return <Loading />
  if (buckets.isError) return <ErrorText error={buckets.error} />
  if (!bucket) return <PageHeader back={back} title="Model not found" />

  const isTarget = settings.data?.target_bucket?.id === bucket.id
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        back={back}
        title={bucket.name}
        meta={
          <>
            {isTarget && (
              <span className="flex items-center gap-1">
                <Badge>Target</Badge>
                <InfoTip label="Target">The model new cash moves you towards.</InfoTip>
              </span>
            )}
            <span>{REBALANCE_LABELS[bucket.rebalance]}</span>
            {bucket.benchmark && <span>vs {bucket.benchmark.fund.name}</span>}
          </>
        }
        actions={
          <>
            {!isTarget && settings.isSuccess && (
              <Button variant="outline" onClick={() => actions.makeTarget(bucket)}>
                <Target /> Set as target
              </Button>
            )}
            <Button asChild variant="outline">
              <Link to={modelPath(bucket.id, 'edit')}>
                <Pencil /> Edit
              </Link>
            </Button>
            <RowActions
              label={`More for ${bucket.name}`}
              actions={[
                {
                  label: 'Delete',
                  icon: Trash2,
                  destructive: true,
                  onSelect: () => void actions.remove(bucket, MODELS_PATH),
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
            path: modelPath(bucket.id),
            label: 'Overview',
            content: <Overview bucket={bucket} isTarget={isTarget} />,
          },
          {
            path: modelPath(bucket.id, 'backtest'),
            label: 'Backtest',
            content: <BacktestWorkspace bucket={bucket} />,
          },
        ]}
      />
    </div>
  )
}

function Overview({ bucket, isTarget }: { bucket: Bucket; isTarget: boolean }) {
  const portfolio = usePortfolio({ enabled: isTarget })
  // Drift is worked out for the target model only (D-071).
  const drift = isTarget ? new Map(portfolio.data?.drift.map((row) => [row.fund.id, row])) : null
  return (
    <>
      {bucket.description && <p className="text-sm">{bucket.description}</p>}
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
            {bucket.funds.map((member) => (
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
      {bucket.benchmark && (
        <Section
          title="Benchmark"
          info={
            <InfoTip label="Benchmark">
              Backtests compare the model with the same money in this fund.
            </InfoTip>
          }
        >
          <Link to={fundPath(bucket.benchmark.fund.id)} className="w-fit hover:underline">
            <FundName fund={bucket.benchmark.fund} />
          </Link>
        </Section>
      )}
    </>
  )
}

/** "-2.50" → "−2.50 pts": the figure is the API's, this only adds the sign and unit. */
function formatPoints(value: string | null | undefined) {
  if (value === null || value === undefined) return '—'
  return formatPercent(value).replace('%', ' pts')
}
