import type { Schemas } from '@/api/client'

export type Bucket = Schemas['BucketOut']
export type Rebalance = Bucket['rebalance']

export const REBALANCE_LABELS: Record<Rebalance, string> = {
  none: 'No rebalancing',
  monthly: 'Rebalance monthly',
  quarterly: 'Rebalance quarterly',
  yearly: 'Rebalance yearly',
}
