import { BriefcaseBusiness, ExternalLink, Plus, Repeat, Wallet } from 'lucide-react'
import { Link, useNavigate } from 'react-router'

import { useHoldings } from '@/api/queries'
import { Table, TBody, Td, Th, THead, Tr } from '@/components/DataTable'
import { EmptyState } from '@/components/EmptyState'
import { ErrorText } from '@/components/Field'
import { Loading } from '@/components/Loading'
import { RowActions } from '@/components/RowActions'
import { Button } from '@/components/ui/button'
import { useAddTransaction } from '@/hooks/use-add-transaction'
import { fundPath, planLabel } from '@/lib/instruments'
import { formatUnits, inr } from '@/lib/money'

/** Every fund I hold: units and what's invested in them. Value and returns come with T1-17. */
export function HoldingsTable() {
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
  return (
    <Table label="Holdings">
      <THead>
        <Th>Fund</Th>
        <Th numeric>Units</Th>
        <Th numeric>Invested</Th>
        <Th numeric>Active SIPs</Th>
        <Th />
      </THead>
      <TBody>
        {holdings.data.map((row) => (
          <Tr key={row.fund.id} to={fundPath(row.fund.id)}>
            <Td>
              <Link
                to={fundPath(row.fund.id)}
                className="font-medium underline-offset-4 hover:underline"
              >
                {row.fund.name}
              </Link>
              {planLabel(row.fund) && (
                <div className="text-muted-foreground text-xs">{planLabel(row.fund)}</div>
              )}
            </Td>
            <Td numeric>{formatUnits(row.units)}</Td>
            <Td numeric>{inr(row.cost)}</Td>
            <Td numeric>{row.active_sips || '—'}</Td>
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
        ))}
      </TBody>
    </Table>
  )
}
