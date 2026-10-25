import { LineChart } from 'lucide-react'
import { Link } from 'react-router'

import { useNavStatus, useSyncNavs } from '@/api/queries'
import { Table, TBody, Td, Th, THead, Tr } from '@/components/DataTable'
import { EmptyState } from '@/components/EmptyState'
import { ErrorText } from '@/components/Field'
import { InfoTip } from '@/components/InfoTip'
import { Loading } from '@/components/Loading'
import { Section } from '@/components/Section'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { fundPath, planLabel } from '@/lib/instruments'
import { RESULT_LABELS, reasonLabel } from '@/lib/navs'
import { formatDate } from '@/lib/time'

/** Funds Friday keeps NAVs for: held, in a model, a benchmark, or tracked by hand. */
export function TrackedFunds() {
  const status = useNavStatus()
  const sync = useSyncNavs()

  return (
    <Section
      title="Tracked funds"
      info={
        <InfoTip label="Tracked funds">
          Funds you hold or track, and every fund and benchmark in a model.
        </InfoTip>
      }
    >
      {status.isPending && <Loading />}
      <ErrorText error={status.error ?? sync.error} />
      {status.isSuccess && status.data.funds.length === 0 && (
        <EmptyState icon={LineChart} title="No funds tracked" />
      )}
      {status.isSuccess && status.data.funds.length > 0 && (
        <Table label="Tracked funds">
          <THead>
            <Th>Fund</Th>
            <Th>Kept for</Th>
            <Th numeric>NAVs</Th>
            <Th>First</Th>
            <Th>Latest</Th>
            <Th>Last sync</Th>
            <Th />
          </THead>
          <TBody>
            {status.data.funds.map((row) => (
              <Tr key={row.fund.id}>
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
                <Td className="text-muted-foreground text-xs">
                  {[...(row.tracked_by_me ? ['You'] : []), ...row.used_by.map(reasonLabel)].join(
                    ', ',
                  )}
                </Td>
                <Td numeric>{row.coverage.count.toLocaleString('en-IN')}</Td>
                <Td className="whitespace-nowrap">
                  {row.coverage.first ? formatDate(row.coverage.first) : '—'}
                </Td>
                <Td className="whitespace-nowrap">
                  {row.coverage.last ? formatDate(row.coverage.last) : '—'}
                </Td>
                <Td>
                  {row.last_result ? (
                    <Badge
                      variant={row.last_result.status === 'failed' ? 'destructive' : 'outline'}
                      title={row.last_result.message ?? undefined}
                    >
                      {RESULT_LABELS[row.last_result.status]}
                    </Badge>
                  ) : (
                    <span className="text-muted-foreground">Never</span>
                  )}
                </Td>
                <Td className="text-right">
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={sync.isPending}
                    onClick={() => sync.mutate([row.fund.id])}
                    aria-label={`Sync ${row.fund.name}`}
                  >
                    Sync
                  </Button>
                </Td>
              </Tr>
            ))}
          </TBody>
        </Table>
      )}
    </Section>
  )
}
