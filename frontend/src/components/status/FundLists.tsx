import { useInstrumentSources } from '@/api/queries'
import type { Schemas } from '@/api/client'
import { ErrorText } from '@/components/Field'
import { InfoTip } from '@/components/InfoTip'
import { Section } from '@/components/Section'
import type { ReactNode } from 'react'
import { formatDateTime } from '@/lib/time'

const SOURCE_LABELS: Record<Schemas['SourceOut']['source'], string> = {
  amfi: 'Mutual funds',
  nse: 'NSE stocks and ETFs',
  us: 'US stocks and ETFs',
}

/** The lists search runs on, and when each was last downloaded. */
export function FundLists({ actions }: { actions?: ReactNode }) {
  const sources = useInstrumentSources()

  return (
    <Section
      title="Fund lists"
      info={<InfoTip label="Fund lists">What search looks through.</InfoTip>}
      actions={actions}
    >
      <ErrorText error={sources.error} />
      {sources.isSuccess && (
        <ul className="divide-y rounded-lg border text-sm">
          {sources.data.map((source) => (
            <li
              key={source.source}
              className="flex flex-wrap justify-between gap-x-4 gap-y-1 px-3 py-2"
            >
              <span className="font-medium">{SOURCE_LABELS[source.source]}</span>
              <span className="text-muted-foreground">
                {source.last_success
                  ? `${source.active_instruments.toLocaleString('en-IN')} active · ${formatDateTime(source.last_success.finished_at)}`
                  : 'Not downloaded'}
              </span>
              {source.last_run?.status === 'failed' && (
                <span className="text-destructive w-full text-xs">
                  Failed {formatDateTime(source.last_run.finished_at)}: {source.last_run.message}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </Section>
  )
}
