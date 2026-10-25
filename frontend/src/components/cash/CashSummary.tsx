import type { Cash } from '@/api/queries'
import { InfoTip } from '@/components/InfoTip'
import { Stat, StatGrid } from '@/components/Stat'
import { inr } from '@/lib/money'

import { PURPOSE_INFO, positive } from './labels'

export function CashSummary({ cash }: { cash: Cash }) {
  const emergency = cash.emergency
  const short = positive(emergency.shortfall)
  return (
    <StatGrid>
      <Stat
        label="Investable"
        info={<InfoTip label="Investable">{PURPOSE_INFO.deployable}</InfoTip>}
        value={inr(cash.deployable)}
      />
      <Stat
        label="Reserved"
        info={<InfoTip label="Reserved">{PURPOSE_INFO.reserved}</InfoTip>}
        value={inr(cash.reserved)}
      />
      <Stat
        label="Emergency"
        info={
          <InfoTip label="Emergency">
            Emergency cash{emergency.fund ? ' plus the emergency fund' : ''}.
          </InfoTip>
        }
        value={inr(emergency.total)}
        hint={`Goal ${inr(emergency.goal)}`}
      />
      <Stat
        label="Emergency shortfall"
        value={short ? inr(emergency.shortfall) : 'None'}
        tone={short ? 'negative' : 'positive'}
      />
    </StatGrid>
  )
}
