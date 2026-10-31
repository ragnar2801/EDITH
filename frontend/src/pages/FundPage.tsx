import { GitCompareArrows, Plus, Repeat, Wallet } from 'lucide-react'
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router'

import {
  useHolding,
  useInstrument,
  usePortfolio,
  type FundPosition,
  type Holding,
} from '@/api/queries'
import { ErrorText } from '@/components/Field'
import { FundDetails } from '@/components/fund/FundDetails'
import { TransactionDialog, type TransactionMode } from '@/components/holdings/TransactionDialog'
import { Transactions } from '@/components/holdings/Transactions'
import { InfoTip } from '@/components/InfoTip'
import { Loading } from '@/components/Loading'
import { NavHistoryCard } from '@/components/NavHistoryCard'
import { PageHeader } from '@/components/PageHeader'
import { RouteTabs } from '@/components/RouteTabs'
import { RowActions } from '@/components/RowActions'
import { Section } from '@/components/Section'
import { Stat, StatGrid } from '@/components/Stat'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog } from '@/components/ui/dialog'
import { comparePath } from '@/lib/compare'
import { hasUnits } from '@/lib/holdings'
import {
  ASSET_CLASS_LABELS,
  fundPath,
  listingLabel,
  planLabel,
  type InstrumentDetail,
} from '@/lib/instruments'
import { formatNav, formatUnits, inr } from '@/lib/money'
import { formatPercent, toneOf } from '@/lib/percent'
import { ROLE_LABELS } from '@/lib/portfolio'
import { formatDate } from '@/lib/time'

/** One page per fund, wherever it's clicked from (J7). */
export function FundPage() {
  const id = Number(useParams().id)
  const instrument = useInstrument(id)
  const back = { to: '/funds', label: 'Funds' }

  if (instrument.isPending) return <Loading />
  if (instrument.isError) {
    return (
      <div className="flex flex-col gap-4">
        <PageHeader back={back} title="Fund not found" />
        <ErrorText error={instrument.error} />
      </div>
    )
  }
  const data = instrument.data
  if (data.kind !== 'mutual_fund') return <OtherInstrument instrument={data} />
  return <Fund fund={data} />
}

function Fund({ fund }: { fund: InstrumentDetail }) {
  const holding = useHolding(fund.id)
  const [mode, setMode] = useState<TransactionMode | null>(null)
  const navigate = useNavigate()
  const held = holding.data?.lots.some(hasUnits) ?? false
  const addLumpSum = (
    <Button onClick={() => setMode({ kind: 'lump-sum' })} disabled={!holding.isSuccess}>
      <Plus /> Add lump sum
    </Button>
  )

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        back={{ to: '/funds', label: 'Funds' }}
        title={fund.name}
        meta={<FundMeta fund={fund} />}
        actions={
          <>
            {addLumpSum}
            {held && (
              <Button variant="outline" onClick={() => setMode({ kind: 'sell' })}>
                <Wallet /> Sell
              </Button>
            )}
            <RowActions
              label={`More for ${fund.name}`}
              actions={[
                {
                  label: 'Start a SIP',
                  icon: Repeat,
                  disabled: !holding.isSuccess,
                  onSelect: () => setMode({ kind: 'sip' }),
                },
                {
                  label: 'Compare',
                  icon: GitCompareArrows,
                  onSelect: () => navigate(comparePath([fund.id])),
                },
              ]}
            />
          </>
        }
      />
      <ErrorText error={holding.error} />
      <RouteTabs
        label="Fund"
        tabs={[
          {
            path: fundPath(fund.id),
            label: 'Overview',
            content: (
              <>
                {holding.data && held && <Position holding={holding.data} />}
                <NavHistoryCard instrumentId={fund.id} />
              </>
            ),
          },
          {
            path: fundPath(fund.id, 'transactions'),
            label: 'Transactions',
            content: holding.data ? (
              <Transactions holding={holding.data} onOpen={setMode} empty={addLumpSum} />
            ) : (
              <Loading />
            ),
          },
          {
            path: fundPath(fund.id, 'details'),
            label: 'Details',
            content: <FundDetails instrument={fund} />,
          },
        ]}
      />
      <Dialog open={mode !== null} onOpenChange={(open) => !open && setMode(null)}>
        {mode && holding.data && (
          <TransactionDialog holding={holding.data} mode={mode} onDone={() => setMode(null)} />
        )}
      </Dialog>
    </div>
  )
}

function FundMeta({ fund }: { fund: InstrumentDetail }) {
  return (
    <>
      {planLabel(fund) && <span>{planLabel(fund)}</span>}
      <Badge variant="outline">{ASSET_CLASS_LABELS[fund.asset_class]}</Badge>
      {!fund.is_active && (
        <span className="flex items-center gap-1">
          <Badge variant="secondary">Inactive</Badge>
          <InfoTip label="Inactive">No longer on its list, or no recent NAV.</InfoTip>
        </span>
      )}
    </>
  )
}

/** Units and cost from the holding; value and returns from the portfolio view. */
function Position({ holding }: { holding: Holding }) {
  const portfolio = usePortfolio()
  const position = portfolio.data?.funds.find((fund) => fund.fund.id === holding.fund.id)
  const result = position?.returns
  return (
    <Section
      title="My position"
      info={
        position && (
          <InfoTip label="My position">
            {ROLE_LABELS[position.role]}
            {result ? `, valued at the NAV of ${formatDate(result.on)}.` : '.'}
          </InfoTip>
        )
      }
    >
      <StatGrid>
        <Stat label="Units held" value={formatUnits(holding.units)} />
        <Stat label="Invested" value={inr(holding.cost)} />
        <Stat
          label="Value"
          value={result ? inr(result.value) : '—'}
          hint={position?.nav ? formatNav(position.nav) : 'No NAV yet'}
        />
        <Stat
          label="Gain"
          value={result ? inr(result.gain) : '—'}
          tone={toneOf(result?.gain)}
          hint={result && formatPercent(result.return_pct)}
        />
        {position && (
          <Returns position={position} benchmarkName={portfolio.data?.benchmark_fund?.name} />
        )}
        <Stat label="Active SIPs" value={holding.sips.filter((sip) => sip.active).length} />
      </StatGrid>
    </Section>
  )
}

function Returns({
  position,
  benchmarkName = 'the benchmark',
}: {
  position: FundPosition
  benchmarkName?: string
}) {
  const result = position.returns
  const benchmark = position.benchmark
  return (
    <>
      <Stat
        label="Unrealised"
        value={position.unrealised === null ? '—' : inr(position.unrealised)}
        tone={toneOf(position.unrealised)}
      />
      <Stat
        label="Realised"
        value={inr(position.realised)}
        tone={toneOf(position.realised)}
        hint={result && `${inr(result.redeemed)} taken out`}
      />
      <Stat
        label="XIRR"
        value={formatPercent(result?.xirr_pct)}
        tone={toneOf(result?.xirr_pct)}
        info={
          <InfoTip label="XIRR">
            Yearly return on your dated purchases and sales, shown once you have held a year.
          </InfoTip>
        }
      />
      <Stat
        label="In the benchmark"
        value={benchmark ? inr(benchmark.value) : '—'}
        hint={benchmark?.xirr_pct ? `XIRR ${formatPercent(benchmark.xirr_pct)}` : undefined}
        info={
          <InfoTip label="In the benchmark">
            Your purchases and sales of this fund, on the same dates, in {benchmarkName}.
          </InfoTip>
        }
      />
    </>
  )
}

/** Only funds are tracked, but an old link to a stock or ETF can still land here. */
function OtherInstrument({ instrument }: { instrument: InstrumentDetail }) {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        back={{ to: '/funds', label: 'Funds' }}
        title={instrument.name}
        meta={
          <>
            <span>{listingLabel(instrument)}</span>
            <Badge variant="outline">{ASSET_CLASS_LABELS[instrument.asset_class]}</Badge>
          </>
        }
      />
      <FundDetails instrument={instrument} />
    </div>
  )
}
