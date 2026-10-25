import { Plus, Repeat, Wallet } from 'lucide-react'
import { useState } from 'react'
import { useParams } from 'react-router'

import { useHolding, useInstrument, type Holding } from '@/api/queries'
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
import { hasUnits } from '@/lib/holdings'
import {
  ASSET_CLASS_LABELS,
  fundPath,
  listingLabel,
  planLabel,
  type InstrumentDetail,
} from '@/lib/instruments'
import { formatUnits, inr } from '@/lib/money'

/** One page per fund, wherever it's clicked from (D-063, J7). */
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

function Position({ holding }: { holding: Holding }) {
  return (
    <Section title="My position">
      <StatGrid>
        <Stat label="Units held" value={formatUnits(holding.units)} />
        <Stat label="Invested" value={inr(holding.cost)} />
        <Stat label="Active SIPs" value={holding.sips.filter((sip) => sip.active).length} />
      </StatGrid>
    </Section>
  )
}

/** Stocks and ETFs aren't part of Phase 1 (D-066), but an old link can still land here. */
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
