import { Link } from 'react-router'

import type { Portfolio } from '@/api/queries'
import { InfoTip } from '@/components/InfoTip'
import { Section } from '@/components/Section'
import { Button } from '@/components/ui/button'
import { fundPath, planLabel } from '@/lib/instruments'
import { investPath } from '@/lib/buckets'
import { modelPath } from '@/lib/models'
import { formatPercent, formatPoints } from '@/lib/percent'

/** How far each fund of the bucket's model is from its weight, with the way to close the
 * gap: new cash through Invest. */
export function ModelDrift({ data }: { data: Portfolio }) {
  if (!data.bucket || !data.model || data.drift.length === 0) return null
  return (
    <Section
      title="Model"
      info={
        <InfoTip label="Model">
          Each fund&apos;s share of what the bucket holds of the model&apos;s funds, against its
          weight.
        </InfoTip>
      }
      actions={
        <>
          <Button asChild size="sm" variant="ghost">
            <Link to={modelPath(data.model.id)}>{data.model.name}</Link>
          </Button>
          <Button asChild size="sm" variant="outline">
            <Link to={investPath(data.bucket.id)}>Invest</Link>
          </Button>
        </>
      }
    >
      <ul className="flex flex-col gap-3 text-sm">
        {data.drift.map((row) => {
          const plan = planLabel(row.fund)
          return (
            <li key={row.fund.id} className="flex flex-col gap-1">
              <div className="flex items-baseline justify-between gap-3">
                <Link
                  to={fundPath(row.fund.id)}
                  className="min-w-0 truncate font-medium underline-offset-4 hover:underline"
                  title={plan ? `${row.fund.name} · ${plan}` : row.fund.name}
                >
                  {row.fund.name}
                </Link>
                <span className="shrink-0 tabular-nums">
                  {formatPercent(row.share, { sign: false })}
                  <span className="text-muted-foreground">
                    {' '}
                    of {formatPercent(row.weight, { sign: false })} · {formatPoints(row.drift)}
                  </span>
                </span>
              </div>
              {/* Widths only draw the bar and the weight's tick; the figures are the API's. */}
              <div className="bg-muted relative h-2 rounded-full" aria-hidden>
                <div
                  className="bg-primary h-full rounded-full"
                  style={{ width: `${row.share ?? 0}%` }}
                />
                <div
                  className="bg-foreground absolute -top-0.5 h-3 w-0.5 rounded"
                  style={{ left: `calc(${row.weight}% - 1px)` }}
                />
              </div>
            </li>
          )
        })}
      </ul>
    </Section>
  )
}
