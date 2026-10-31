import type { Schemas } from '@/api/client'
import { planLabel } from '@/lib/instruments'

/** A fund's name with its plan underneath (D-060: identity, not identifiers). */
export function FundName({ fund }: { fund: Pick<Schemas['FundRef'], 'name' | 'plan' | 'option'> }) {
  const plan = planLabel(fund)
  return (
    <span className="flex min-w-0 flex-col">
      <span className="truncate font-medium">{fund.name}</span>
      {plan && <span className="text-muted-foreground truncate text-xs">{plan}</span>}
    </span>
  )
}
