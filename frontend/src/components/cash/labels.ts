import type { CashAccount } from '@/api/queries'

export type Purpose = CashAccount['earmark']

/** UI words for the API's earmarks. */
export const PURPOSE_LABELS: Record<Purpose, string> = {
  deployable: 'Investable',
  reserved: 'Reserved',
  emergency: 'Emergency',
}

export const PURPOSE_INFO: Record<Purpose, string> = {
  deployable: 'What Invest may use.',
  reserved: 'Set aside for something known; never invested.',
  emergency: 'Topped up to the emergency goal first; never invested.',
}

/** Is a decimal string from the API above zero? Checked on the string, no arithmetic. */
export function positive(amount: string): boolean {
  return !amount.startsWith('-') && /[1-9]/.test(amount)
}
