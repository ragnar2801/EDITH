/**
 * Show a percentage from the API ("12.34", "-0.49") with its sign: "+12.34%", "−0.49%".
 * The value is already rounded by the backend; this only adds the sign and the % mark.
 */
export function formatPercent(value: string | null | undefined, { sign = true } = {}): string {
  if (value === null || value === undefined) return '—'
  const negative = value.startsWith('-')
  const digits = negative ? value.slice(1) : value
  const zero = /^0+(\.0+)?$/.test(digits)
  const prefix = negative && !zero ? '−' : sign && !zero ? '+' : ''
  return `${prefix}${digits}%`
}

/** Colour for a signed figure from the API ("12.34", "-0.49"); zero gets none. */
export function toneOf(value: string | null | undefined): 'positive' | 'negative' | undefined {
  if (!value || /^-?0*(\.0+)?$/.test(value)) return undefined
  return value.startsWith('-') ? 'negative' : 'positive'
}
