import { Link, useNavigate } from 'react-router'

import { useHoldings } from '@/api/queries'
import { InstrumentSearch } from '@/components/InstrumentSearch'
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { planLabel } from '@/lib/instruments'
import { formatUnits, inr } from '@/lib/money'
import { formatDate } from '@/lib/time'

export function HoldingsPage() {
  const holdings = useHoldings()
  const navigate = useNavigate()

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Holdings</h1>
        <p className="text-muted-foreground mt-1">
          The funds you own: lump sums and SIPs, and the units and cost you still hold. Value and
          returns arrive with the dashboard (T1-17).
        </p>
      </div>

      <InstrumentSearch
        kind="mutual_fund"
        label="Add a fund"
        placeholder="Add a lump sum or SIP: fund name or AMFI scheme code"
        onSelect={(fund) => navigate(`/holdings/${fund.id}`)}
      />

      {holdings.isError && <p className="text-destructive text-sm">{holdings.error.message}</p>}
      {holdings.isSuccess && holdings.data.length === 0 && (
        <Card>
          <CardHeader>
            <CardTitle>No holdings yet</CardTitle>
            <CardDescription>
              Find a fund above, then add a lump sum or start a SIP. Friday fills in each SIP
              instalment from the fund&apos;s NAVs.
            </CardDescription>
          </CardHeader>
        </Card>
      )}
      {holdings.isSuccess && holdings.data.length > 0 && (
        <div className="overflow-x-auto rounded-lg border">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-muted-foreground text-left text-xs">
              <tr>
                <th className="px-3 py-2 font-medium">Fund</th>
                <th className="px-3 py-2 text-right font-medium">Units</th>
                <th className="px-3 py-2 text-right font-medium">Cost</th>
                <th className="px-3 py-2 text-right font-medium">Lots</th>
                <th className="px-3 py-2 text-right font-medium">Active SIPs</th>
                <th className="px-3 py-2 text-right font-medium">NAVs to</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {holdings.data.map((row) => (
                <tr key={row.fund.id}>
                  <td className="px-3 py-2">
                    <Link
                      to={`/holdings/${row.fund.id}`}
                      className="font-medium underline-offset-4 hover:underline"
                    >
                      {row.fund.name}
                    </Link>
                    <div className="text-muted-foreground text-xs">
                      AMFI {row.fund.amfi_code}
                      {planLabel(row.fund) && ` · ${planLabel(row.fund)}`}
                    </div>
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">{formatUnits(row.units)}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{inr(row.cost)}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{row.lots}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{row.active_sips}</td>
                  <td className="text-muted-foreground px-3 py-2 text-right">
                    {row.nav_last ? formatDate(row.nav_last) : 'none yet'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
