import { Link, useNavigate } from 'react-router'

import { useNavStatus } from '@/api/queries'
import { InstrumentSearch } from '@/components/InstrumentSearch'
import { PageHeader } from '@/components/PageHeader'
import { Section } from '@/components/Section'
import { fundPath, planLabel } from '@/lib/instruments'
import { reasonLabel } from '@/lib/navs'

/** Find a fund (J7); the funds Friday already follows are one click away. */
export function FundsPage() {
  const navigate = useNavigate()
  const status = useNavStatus()
  const funds = status.data?.funds ?? []

  return (
    <div className="flex max-w-3xl flex-col gap-8">
      <PageHeader title="Funds" />
      <InstrumentSearch
        autoFocus
        kind="mutual_fund"
        onSelect={(fund) => navigate(fundPath(fund.id))}
      />
      {funds.length > 0 && (
        <Section title="Followed">
          <ul className="divide-y rounded-lg border text-sm">
            {funds.map((row) => (
              <li key={row.fund.id}>
                <Link
                  to={fundPath(row.fund.id)}
                  className="hover:bg-muted/40 flex flex-wrap items-center gap-x-3 gap-y-0.5 px-3 py-2"
                >
                  <span className="flex min-w-0 flex-col">
                    <span className="font-medium">{row.fund.name}</span>
                    {planLabel(row.fund) && (
                      <span className="text-muted-foreground text-xs">{planLabel(row.fund)}</span>
                    )}
                  </span>
                  <span className="text-muted-foreground ml-auto text-xs">
                    {[...(row.tracked_by_me ? ['You'] : []), ...row.used_by.map(reasonLabel)].join(
                      ', ',
                    )}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </Section>
      )}
    </div>
  )
}
