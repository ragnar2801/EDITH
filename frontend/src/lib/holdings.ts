import type { Schemas } from '@/api/client'

export type Lot = Schemas['LotOut']
export type Sip = Schemas['SipOut']

/** Units left in a lot? Checked on the decimal string: no arithmetic on amounts (D-032). */
export function hasUnits(lot: Lot): boolean {
  return !lot.skipped && /[1-9]/.test(lot.units_remaining)
}

export const KIND_LABELS: Record<Lot['kind'], string> = {
  lump_sum: 'Lump sum',
  sip: 'SIP',
}
