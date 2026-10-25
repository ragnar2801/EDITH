import { BriefcaseBusiness } from 'lucide-react'
import { Link, useNavigate } from 'react-router'

import { useHoldings } from '@/api/queries'
import { Table, TBody, Td, Th, THead, Tr } from '@/components/DataTable'
import { EmptyState } from '@/components/EmptyState'
import { ErrorText } from '@/components/Field'
import { InstrumentSearch } from '@/components/InstrumentSearch'
import { Loading } from '@/components/Loading'
import { PageHeader } from '@/components/PageHeader'
import { planLabel } from '@/lib/instruments'
import { formatUnits, inr } from '@/lib/money'

export function HoldingsPage() {
  const holdings = useHoldings()
  const navigate = useNavigate()

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <PageHeader title="Holdings" />
      <div className="max-w-md">
        <InstrumentSearch
          kind="mutual_fund"
          label="Add a fund"
          placeholder="Add a fund"
          onSelect={(fund) => navigate(`/holdings/${fund.id}`)}
        />
      </div>

      <ErrorText error={holdings.error} />
      {holdings.isPending && <Loading />}
      {holdings.isSuccess && holdings.data.length === 0 && (
        <EmptyState icon={BriefcaseBusiness} title="No holdings yet" />
      )}
      {holdings.isSuccess && holdings.data.length > 0 && (
        <Table label="Holdings">
          <THead>
            <Th>Fund</Th>
            <Th numeric>Units</Th>
            <Th numeric>Invested</Th>
            <Th numeric>Active SIPs</Th>
          </THead>
          <TBody>
            {holdings.data.map((row) => (
              <Tr key={row.fund.id} to={`/holdings/${row.fund.id}`}>
                <Td>
                  <Link
                    to={`/holdings/${row.fund.id}`}
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
              </Tr>
            ))}
          </TBody>
        </Table>
      )}
    </div>
  )
}
