import { useParams } from 'react-router'

import { useInstrument } from '@/api/queries'
import { ErrorText } from '@/components/Field'
import { FundDetails } from '@/components/fund/FundDetails'
import { InfoTip } from '@/components/InfoTip'
import { Loading } from '@/components/Loading'
import { NavHistoryCard } from '@/components/NavHistoryCard'
import { PageHeader } from '@/components/PageHeader'
import { Badge } from '@/components/ui/badge'
import { ASSET_CLASS_LABELS, listingLabel, planLabel } from '@/lib/instruments'

export function InstrumentPage() {
  const id = Number(useParams().id)
  const instrument = useInstrument(id)
  const back = { to: '/instruments', label: 'Funds' }

  if (instrument.isPending) return <Loading />
  if (instrument.isError) {
    return (
      <div className="mx-auto flex max-w-3xl flex-col gap-4">
        <PageHeader back={back} title="Fund not found" />
        <ErrorText error={instrument.error} />
      </div>
    )
  }

  const data = instrument.data
  const isFund = data.kind === 'mutual_fund'
  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-8">
      <PageHeader
        back={back}
        title={data.name}
        meta={
          <>
            <span>{isFund ? planLabel(data) : listingLabel(data)}</span>
            <Badge variant="outline">{ASSET_CLASS_LABELS[data.asset_class]}</Badge>
            {!data.is_active && (
              <span className="flex items-center gap-1">
                <Badge variant="secondary">Inactive</Badge>
                <InfoTip label="Inactive">No longer on its list, or no recent NAV.</InfoTip>
              </span>
            )}
          </>
        }
      />
      {data.amfi_code && <NavHistoryCard instrumentId={data.id} />}
      <FundDetails instrument={data} />
    </div>
  )
}
