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

/** Short form for tiles and chart axes: ₹12.35L, ₹1.2Cr, ₹98.77K. Same rule: no arithmetic. */
export function formatMoneyShort({ amount, currency }: Money): string {
  return new Intl.NumberFormat(LOCALES[currency], {
    style: 'currency',
    currency,
    notation: 'compact',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(amount as Intl.StringNumericLiteral)
}

const NAV = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  minimumFractionDigits: 2,
  maximumFractionDigits: 8,
})

/** A fund NAV with every place it was published with (D-045): ₹14.86269632, ₹88.9695. */
export function formatNav(nav: string): string {
  return NAV.format(nav as Intl.StringNumericLiteral)
}

/** An INR amount, the common case. */
export function inr(amount: string): string {
  return formatMoney({ amount, currency: 'INR' })
}

export function inrShort(amount: string): string {
  return formatMoneyShort({ amount, currency: 'INR' })
}
