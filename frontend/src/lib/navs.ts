import type { Schemas } from '@/api/client'

export type SyncRun = Schemas['SyncRunOut']
type FundResult = Schemas['FundResultOut']

export const RESULT_LABELS: Record<FundResult['status'], string> = {
  ok: 'OK',
  fallback: 'Latest only',
  failed: 'Failed',
}

/** "Synced 26 NAVs for 2 funds", or which funds had trouble. */
export function syncMessage(run: SyncRun): string {
  const funds = `${run.funds} fund${run.funds === 1 ? '' : 's'}`
  return `${run.added.toLocaleString('en-IN')} NAVs added for ${funds}`
}

/** Why a fund is tracked, in UI words (D-061): the API says "bucket Core", "holding". */
export function reasonLabel(reason: string): string {
  if (reason === 'holding') return 'Holding'
  if (reason.startsWith('bucket ')) return `Model ${reason.slice('bucket '.length)}`
  return reason.charAt(0).toUpperCase() + reason.slice(1)
}
