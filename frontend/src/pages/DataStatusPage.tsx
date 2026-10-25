import { NavSync } from '@/components/data/NavSync'
import { TrackedFunds } from '@/components/data/TrackedFunds'
import { PageHeader } from '@/components/PageHeader'

export function DataStatusPage() {
  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-8">
      <PageHeader title="Data status" />
      <NavSync />
      <TrackedFunds />
    </div>
  )
}
