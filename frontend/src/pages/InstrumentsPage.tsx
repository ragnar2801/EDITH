import { useNavigate } from 'react-router'

import { FundLists } from '@/components/data/FundLists'
import { InstrumentSearch } from '@/components/InstrumentSearch'
import { PageHeader } from '@/components/PageHeader'
import { fundPath } from '@/lib/instruments'

export function InstrumentsPage() {
  const navigate = useNavigate()

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-8">
      <PageHeader title="Funds" />
      <InstrumentSearch autoFocus onSelect={(instrument) => navigate(fundPath(instrument.id))} />
      <FundLists />
    </div>
  )
}
