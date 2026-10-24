import type { Schemas } from '@/api/client'

export type Money = Schemas['Money']

const LOCALES: Record<Money['currency'], string> = {
  INR: 'en-IN', // Indian digit grouping: ₹12,34,567.89
  USD: 'en-US',
}

/**
 * Format an amount for display. Amounts arrive as exact decimal strings (D-032) and are
 * passed to Intl as strings, so no digit is lost to floating point. Never do arithmetic
 * on amounts in the frontend: the backend computes every figure.
 */
export function formatMoney({ amount, currency }: Money): string {
  return new Intl.NumberFormat(LOCALES[currency], { style: 'currency', currency }).format(
    amount as Intl.StringNumericLiteral,
  )
}
