import { Plus, Repeat } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router'

import { useHolding } from '@/api/queries'
import { ErrorText } from '@/components/Field'
import { TransactionDialog, type TransactionMode } from '@/components/holdings/TransactionDialog'
import { Transactions } from '@/components/holdings/Transactions'
import { Loading } from '@/components/Loading'
import { PageHeader } from '@/components/PageHeader'
import { Stat, StatGrid } from '@/components/Stat'
import { Button } from '@/components/ui/button'
import { Dialog } from '@/components/ui/dialog'
import { hasUnits } from '@/lib/holdings'
import { fundPath, planLabel } from '@/lib/instruments'
import { formatUnits, inr } from '@/lib/money'

export function HoldingPage() {
  const id = Number(useParams().id)
  const holding = useHolding(id)
  const [mode, setMode] = useState<TransactionMode | null>(null)

  if (holding.isPending) return <Loading />
  if (holding.isError) return <ErrorText error={holding.error} />

  const data = holding.data
  const addLumpSum = (
    <Button onClick={() => setMode({ kind: 'lump-sum' })}>
      <Plus /> Add lump sum
    </Button>
  )
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-8">
      <PageHeader
        back={{ to: '/holdings', label: 'Holdings' }}
        title={data.fund.name}
        meta={
          <>
            {planLabel(data.fund) && <span>{planLabel(data.fund)}</span>}
            <Link to={fundPath(data.fund.id)} className="underline-offset-4 hover:underline">
              Fund details
            </Link>
          </>
        }
        actions={
          <>
            {addLumpSum}
            <Button variant="outline" onClick={() => setMode({ kind: 'sip' })}>
              <Repeat /> Start a SIP
            </Button>
            <Button
              variant="outline"
              disabled={!data.lots.some(hasUnits)}
              onClick={() => setMode({ kind: 'sell' })}
            >
              Sell units
            </Button>
          </>
        }
      />

      <StatGrid>
        <Stat label="Units held" value={formatUnits(data.units)} />
        <Stat label="Invested" value={inr(data.cost)} />
        <Stat label="Active SIPs" value={data.sips.filter((sip) => sip.active).length} />
      </StatGrid>

      <Transactions holding={data} onOpen={setMode} empty={addLumpSum} />

      <Dialog open={mode !== null} onOpenChange={(open) => !open && setMode(null)}>
        {mode && <TransactionDialog holding={data} mode={mode} onDone={() => setMode(null)} />}
      </Dialog>
    </div>
  )
}
