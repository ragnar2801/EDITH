import type { FundPosition, Portfolio } from '@/api/queries'

export const ASSET_LABELS: Record<Portfolio['allocation'][number]['asset'], string> = {
  equity: 'Equity',
  debt: 'Debt',
  gold: 'Gold',
  silver: 'Silver',
  other: 'Other',
  unclassified: 'Unclassified',
}

export const ROLE_LABELS: Record<FundPosition['role'], string> = {
  target: 'In the target model',
  emergency: 'Emergency fund',
  outside: 'Outside the target model',
}
