/**
 * Model weights while editing: percentages with up to 2 decimal places, handled as
 * whole basis points so the running total is exact. The backend checks the same rule
 * (the weights add up to exactly 100) when the model is saved.
 */

const WEIGHT = /^\d{1,3}(\.\d{1,2})?$/

/** "33.33" → 3333; anything that isn't a 0–100 weight with ≤ 2 places → null. */
export function toBasisPoints(weight: string): number | null {
  const text = weight.trim()
  if (!WEIGHT.test(text)) return null
  const [whole, fraction = ''] = text.split('.')
  const points = Number(whole) * 100 + Number(fraction.padEnd(2, '0'))
  return points <= 10_000 ? points : null
}

/** 3333 → "33.33", 9990 → "99.9", 6000 → "60". */
export function fromBasisPoints(points: number): string {
  const whole = Math.floor(points / 100)
  const fraction = String(points % 100)
    .padStart(2, '0')
    .replace(/0+$/, '')
  return fraction ? `${whole}.${fraction}` : String(whole)
}

/** Total of the weights, or null if any is not a valid weight. */
export function totalBasisPoints(weights: string[]): number | null {
  let total = 0
  for (const weight of weights) {
    const points = toBasisPoints(weight)
    if (points === null) return null
    total += points
  }
  return total
}

/** `count` weights adding up to exactly 100; the first ones get the leftover hundredths. */
export function equalWeights(count: number): string[] {
  if (count <= 0) return []
  const base = Math.floor(10_000 / count)
  const extra = 10_000 - base * count
  return Array.from({ length: count }, (_, i) => fromBasisPoints(base + (i < extra ? 1 : 0)))
}
