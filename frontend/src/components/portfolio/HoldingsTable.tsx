import { BriefcaseBusiness, ExternalLink, Plus, Repeat, Wallet } from 'lucide-react'
import { Link, useNavigate } from 'react-router'

import { useHoldings, type Portfolio } from '@/api/queries'
import { Table, TBody, Td, Th, THead, Tr } from '@/components/DataTable'
import { EmptyState } from '@/components/EmptyState'
import { ErrorText } from '@/components/Field'
import { InfoTip } from '@/components/InfoTip'
import { Loading } from '@/components/Loading'
import { RowActions } from '@/components/RowActions'
import { Button } from '@/components/ui/button'
import { useAddTransaction } from '@/hooks/use-add-transaction'
import { fundPath, planLabel } from '@/lib/instruments'
import { formatUnits, inr } from '@/lib/money'
import { formatPercent, toneOf } from '@/lib/percent'

/** Every fund I hold: units, what's invested, and (from the portfolio view) value, gain, weight
 * and target weight (D-070). */
export function HoldingsTable({ portfolio }: { portfolio?: Portfolio }) {
  const holdings = useHoldings()
  const addTransaction = useAddTransaction()
  const navigate = useNavigate()

  if (holdings.isPending) return <Loading />
  if (holdings.isError) return <ErrorText error={holdings.error} />
  if (holdings.data.length === 0) {
    return (
      <EmptyState
        icon={BriefcaseBusiness}
        title="No funds yet"
        action={
          <Button onClick={() => addTransaction()}>
            <Plus /> Add transaction
          </Button>
        }
      />
    )
  }
  const positions = new Map(portfolio?.funds.map((fund) => [fund.fund.id, fund]))
  const targets = new Map(portfolio?.drift.map((row) => [row.fund.id, row.weight]))
  return (
    <Table label="Holdings">
      <THead>
        <Th>Fund</Th>
        <Th numeric>Units</Th>
        <Th numeric>Invested</Th>
        <Th numeric>Value</Th>
        <Th numeric>Gain</Th>
        <Th numeric>Weight</Th>
        <Th numeric>
          <span className="inline-flex items-center gap-1">
            Target
            <InfoTip label="Target">The fund&apos;s weight in your target model.</InfoTip>
          </span>
        </Th>
        <Th />
      </THead>
      <TBody>
        {holdings.data.map((row) => {
          const position = positions.get(row.fund.id)
          const result = position?.returns
          const target = targets.get(row.fund.id)
          const notes = [
            planLabel(row.fund),
            row.active_sips > 0 && `${row.active_sips} SIP${row.active_sips === 1 ? '' : 's'}`,
            position?.role === 'emergency' && 'Emergency fund',
          ].filter(Boolean)
          return (
            <Tr key={row.fund.id} to={fundPath(row.fund.id)}>
              <Td>
                <Link
                  to={fundPath(row.fund.id)}
                  className="font-medium underline-offset-4 hover:underline"
                >
                  {row.fund.name}
                </Link>
                {notes.length > 0 && (
                  <div className="text-muted-foreground text-xs">{notes.join(' · ')}</div>
                )}
              </Td>
              <Td numeric>{formatUnits(row.units)}</Td>
              <Td numeric>{inr(row.cost)}</Td>
              <Td numeric>{result ? inr(result.value) : '—'}</Td>
              <Td numeric>
                {result ? (
                  <span className={gainClass(result.gain)}>
                    {inr(result.gain)}
                    <span className="block text-xs">{formatPercent(result.return_pct)}</span>
                  </span>
                ) : (
                  '—'
                )}
              </Td>
              <Td numeric>{formatPercent(position?.share, { sign: false })}</Td>
              <Td numeric>{target ? formatPercent(target, { sign: false }) : '—'}</Td>
              <Td className="w-0">
                <RowActions
                  label={`Actions for ${row.fund.name}`}
                  actions={[
                    {
                      label: 'Add lump sum',
                      icon: Plus,
                      onSelect: () => addTransaction(row.fund, 'lump-sum'),
                    },
                    {
                      label: 'Start a SIP',
                      icon: Repeat,
                      onSelect: () => addTransaction(row.fund, 'sip'),
                    },
                    {
                      label: 'Sell',
                      icon: Wallet,
                      disabled: !/[1-9]/.test(row.units),
                      onSelect: () => addTransaction(row.fund, 'sell'),
                    },
                    {
                      label: 'Open fund',
                      icon: ExternalLink,
                      onSelect: () => navigate(fundPath(row.fund.id)),
                    },
                  ]}
                />
              </Td>
            </Tr>
          )
        })}
      </TBody>
    </Table>
  )
}

function gainClass(value: string) {
  const tone = toneOf(value)
  return tone === 'positive' ? 'text-positive' : tone === 'negative' ? 'text-destructive' : ''
}
