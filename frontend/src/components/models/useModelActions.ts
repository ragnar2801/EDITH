import { useNavigate } from 'react-router'
import { toast } from 'sonner'

import { useDeleteBucket, useSetTarget } from '@/api/queries'
import { useConfirm } from '@/hooks/use-confirm'
import type { Bucket } from '@/lib/buckets'

/** Set as target and delete, with their toasts and confirm, for a list row or a model page. */
export function useModelActions() {
  const setTarget = useSetTarget()
  const remove = useDeleteBucket()
  const confirm = useConfirm()
  const navigate = useNavigate()

  return {
    error: setTarget.error ?? remove.error,
    makeTarget: (bucket: Bucket) =>
      setTarget.mutate(bucket.id, {
        onSuccess: () => toast.success(`${bucket.name} is your target`),
      }),
    remove: async (bucket: Bucket, then?: string) => {
      const yes = await confirm({
        title: `Delete ${bucket.name}?`,
        description: 'Its saved backtests are deleted too.',
      })
      if (!yes) return
      remove.mutate(bucket.id, {
        onSuccess: () => {
          toast.success(`${bucket.name} deleted`)
          if (then) navigate(then)
        },
      })
    },
  }
}
