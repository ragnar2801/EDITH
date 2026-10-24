import { useNavigate } from 'react-router'

import { useInstrumentSources } from '@/api/queries'
import type { Schemas } from '@/api/client'
import { InstrumentSearch } from '@/components/InstrumentSearch'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { formatDateTime } from '@/lib/time'

const SOURCE_LABELS: Record<Schemas['SourceOut']['source'], string> = {
  nse: 'NSE stocks and ETFs',
  amfi: 'Mutual funds (AMFI)',
  us: 'US stocks and ETFs',
}

export function InstrumentsPage() {
  const navigate = useNavigate()

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Instruments</h1>
        <p className="text-muted-foreground mt-1">
          Every NSE stock and ETF, Indian mutual fund and US stock and ETF Friday knows about.
        </p>
      </div>
      <InstrumentSearch
        autoFocus
        onSelect={(instrument) => navigate(`/instruments/${instrument.id}`)}
      />
      <SourcesCard />
    </div>
  )
}

function SourcesCard() {
  const sources = useInstrumentSources()
  const neverRefreshed = sources.isSuccess && sources.data.every((source) => !source.last_success)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Lists</CardTitle>
        <CardDescription>
          Refresh them with <code>just instruments</code> in the Friday folder.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {sources.isError && <p className="text-destructive text-sm">{sources.error.message}</p>}
        {neverRefreshed && (
          <p className="text-muted-foreground mb-3 text-sm">
            No lists imported yet, so search will find nothing until the first refresh.
          </p>
        )}
        {sources.isSuccess && (
          <ul className="divide-y text-sm">
            {sources.data.map((source) => (
              <li
                key={source.source}
                className="flex flex-wrap justify-between gap-x-4 gap-y-1 py-2"
              >
                <span className="font-medium">{SOURCE_LABELS[source.source]}</span>
                <span className="text-muted-foreground">
                  {source.last_success
                    ? `${source.active_instruments.toLocaleString('en-IN')} active · refreshed ${formatDateTime(source.last_success.finished_at)}`
                    : 'never refreshed'}
                </span>
                {source.last_run?.status === 'failed' && (
                  <span className="text-destructive w-full text-xs">
                    Last refresh failed ({formatDateTime(source.last_run.finished_at)}):{' '}
                    {source.last_run.message}
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
