import type { Schemas } from '@/api/client'

type BucketRef = Pick<Schemas['BucketRef'], 'id' | 'name' | 'paper'>

/** The Funds tab of Portfolio showing one bucket. */
export function bucketPath(id: number): string {
  return `/?bucket=${id}`
}

/** Invest, planning for one bucket. */
export function investPath(id: number): string {
  return `/invest?bucket=${id}`
}

export function bucketLabel(bucket: BucketRef): string {
  return bucket.paper ? `${bucket.name} (paper)` : bucket.name
}

/** A bucket id from the address, if it is one. */
export function bucketParam(value: string | null): number | undefined {
  const id = Number(value)
  return value && Number.isInteger(id) && id > 0 ? id : undefined
}
