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

/** Every fund I hold, biggest first: what's invested, and (from the portfolio view) value,
 * gain, the day's move, XIRR, the gap to the benchmark, weight and target weight (D-070,
 * D-072, D-073). */
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
  const positions = new Map(portfolio?.funds.map((fund, i) => [fund.fund.id, { fund, i }]))
  const targets = new Map(portfolio?.drift.map((row) => [row.fund.id, row.weight]))
  const benchmark = portfolio?.benchmark_fund?.name ?? 'the benchmark'
  // The portfolio lists funds biggest first; a SIP with no instalment yet comes last.
  const rows = [...holdings.data].sort(
    (a, b) => (positions.get(a.fund.id)?.i ?? Infinity) - (positions.get(b.fund.id)?.i ?? Infinity),
  )
  return (
    <Table label="Holdings">
      <THead>
        <Th className="min-w-48">Fund</Th>
        <Th numeric>Invested</Th>
        <Th numeric>Value</Th>
        <Th numeric>Gain</Th>
        <Th numeric>
          <span className="inline-flex items-center gap-1">
            Day
            <InfoTip label="Day">Change between the fund&apos;s last two NAVs.</InfoTip>
          </span>
        </Th>
        <Th numeric>XIRR</Th>
        <Th numeric>
          <span className="inline-flex items-center gap-1">
            vs benchmark
            <InfoTip label="vs benchmark">
              The fund&apos;s gain minus the same money&apos;s in {benchmark}.
            </InfoTip>
          </span>
        </Th>
        <Th numeric>
          <span className="inline-flex items-center gap-1">
            Weight
            <InfoTip label="Weight">
              Share of what your funds are worth; below it, the fund&apos;s weight in your target
              model.
            </InfoTip>
          </span>
        </Th>
        <Th />
      </THead>
      <TBody>
        {rows.map((row) => {
          const position = positions.get(row.fund.id)?.fund
          const result = position?.returns
          const target = targets.get(row.fund.id)
          const sold = !/[1-9]/.test(row.units)
          const notes = [
            planLabel(row.fund),
            row.active_sips > 0 && `${row.active_sips} SIP${row.active_sips === 1 ? '' : 's'}`,
            position?.role === 'emergency' && 'Emergency fund',
            sold && 'Sold',
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
              <Td numeric>{inr(row.cost)}</Td>
              <Td numeric>
                {result ? inr(result.value) : '—'}
                <span className="text-muted-foreground block text-xs">
                  {formatUnits(row.units)} units
                </span>
              </Td>
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
              <Td numeric>
                {position?.day && !sold ? (
                  <span className={gainClass(position.day.gain)}>
                    {inr(position.day.gain)}
                    <span className="block text-xs">{formatPercent(position.day.return_pct)}</span>
                  </span>
                ) : (
                  '—'
                )}
              </Td>
              <Td numeric>
                <span className={gainClass(result?.xirr_pct)}>
                  {formatPercent(result?.xirr_pct)}
                </span>
              </Td>
              <Td numeric>
                {position?.ahead ? (
                  <span className={gainClass(position.ahead)}>{inr(position.ahead)}</span>
                ) : (
                  '—'
                )}
              </Td>
              <Td numeric>
                {formatPercent(position?.share, { sign: false })}
                {target && (
                  <span className="text-muted-foreground block text-xs">
                    of {formatPercent(target, { sign: false })}
                  </span>
                )}
              </Td>
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
                      disabled: sold,
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

function gainClass(value: string | null | undefined) {
  const tone = toneOf(value)
  return tone === 'positive' ? 'text-positive' : tone === 'negative' ? 'text-destructive' : ''
}
